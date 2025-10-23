# scans/processing/pipeline.py

import requests
import time
import os
import tempfile
import trimesh
from django.conf import settings
from django.core.files import File
from ..mesh_measurements import perform_all_measurements

class PipelineError(Exception):
    pass

def _get_api_headers(api_key):
    """
    Returns the Authorization header with Bearer token.
    According to Swagger UI: bearerAuth (http, Bearer)
    """
    return {'Authorization': f'Bearer {api_key}'}

def _init_avatar(api_key):
    """Step 1: Initialize the avatar."""
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, 'avatar/init')
    headers = _get_api_headers(api_key)
    payload = {"photos_count": 1}

    # Debug logging to help troubleshoot
    print(f"--- Step 1: POST to {url} ---")
    print(f"DEBUG - API Key exists: {bool(api_key)}")
    print(f"DEBUG - API Key length: {len(api_key) if api_key else 0}")
    print(f"DEBUG - API Key (first 10 chars): {api_key[:10] if api_key and len(api_key) >= 10 else 'TOO_SHORT'}")
    print(f"DEBUG - API Key (last 10 chars): {api_key[-10:] if api_key and len(api_key) >= 10 else 'TOO_SHORT'}")
    print(f"DEBUG - Headers being sent: {{'Authorization': 'Bearer {api_key[:10]}...{api_key[-10:]}'}}") 
    print(f"DEBUG - Payload: {payload}")
    
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"ERROR - Response Status: {response.status_code}")
        print(f"ERROR - Response Body: {response.text}")
        print(f"ERROR - Response Headers: {dict(response.headers)}")
        
        # Check for specific error types
        if response.status_code == 403:
            print("\n!!! AUTHENTICATION FAILED !!!")
            print("Possible causes:")
            print("1. API key is invalid or expired")
            print("2. API key doesn't have permission for this endpoint")
            print("3. API key format is wrong (check for extra spaces/newlines)")
            print("4. Account may need to be activated or verified")
            print("\nPlease verify your KEENTOOLS_SECRET_KEY in your environment variables.")
            print("Make sure you copied the FULL key from the KeenTools dashboard.")
        
        raise PipelineError(f"Init failed: {response.status_code} - {response.text}")
    
    data = response.json()
    avatar_id = data.get('avatar_id')
    upload_url = data.get('presigned_urls', [{}])[0].get('url')
    
    if not avatar_id or not upload_url:
        raise PipelineError(f"Invalid init response. Got: {data}")
    
    print(f"--- Avatar initialized successfully. ID: {avatar_id} ---")
    return avatar_id, upload_url

def _upload_photo(upload_url, image_path):
    """Step 2: Upload photo to S3."""
    print(f"--- Step 2: Uploading photo to S3 ---")
    
    if not os.path.exists(image_path):
        raise PipelineError(f"Image file not found: {image_path}")
    
    try:
        with open(image_path, 'rb') as f:
            headers = {'Content-Type': 'image/jpeg'}
            response = requests.put(upload_url, headers=headers, data=f)
            
            if response.status_code != 200:
                print(f"ERROR - S3 Upload Status: {response.status_code}")
                print(f"ERROR - S3 Upload Response: {response.text}")
                raise PipelineError(f"S3 upload failed: {response.status_code} - {response.text}")
        
        print("--- Photo uploaded successfully. ---")
    except Exception as e:
        raise PipelineError(f"Photo upload error: {str(e)}")

def _start_reconstruction(api_key, avatar_id):
    """Step 3: Start reconstruction."""
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/create')
    headers = _get_api_headers(api_key)
    
    print(f"--- Step 3: Starting reconstruction for avatar {avatar_id} ---")
    response = requests.post(url, headers=headers)
    
    if response.status_code != 200:
        print(f"ERROR - Start Reconstruction Status: {response.status_code}")
        print(f"ERROR - Start Reconstruction Response: {response.text}")
        raise PipelineError(f"Start reconstruction failed: {response.status_code} - {response.text}")
    
    print("--- Reconstruction started successfully. ---")

def _poll_for_completion(api_key, avatar_id, timeout=300):
    """Step 4: Check job status."""
    status_url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/get_status')
    headers = _get_api_headers(api_key)
    start_time = time.time()
    
    print(f"--- Step 4: Polling for completion (timeout: {timeout}s) ---")
    
    poll_count = 0
    while time.time() - start_time < timeout:
        poll_count += 1
        response = requests.get(status_url, headers=headers)
        
        if response.status_code != 200:
            print(f"ERROR - Polling Status: {response.status_code}")
            print(f"ERROR - Polling Response: {response.text}")
            raise PipelineError(f"Polling failed: {response.status_code} - {response.text}")
        
        data = response.json()
        status = data.get('status')
        elapsed = int(time.time() - start_time)
        
        print(f"Poll #{poll_count} ({elapsed}s elapsed): Status = {status}")
        
        if status == 'completed':
            print(f"--- Job completed successfully after {elapsed}s ---")
            return
        elif status == 'failed':
            error_msg = data.get('error', 'Unknown error')
            print(f"ERROR - Job failed: {error_msg}")
            raise PipelineError(f"KeenTools job failed: {error_msg}")
        
        time.sleep(15)
    
    raise PipelineError(f"Job timed out after {timeout}s")

def _download_and_save_model(scan, api_key, avatar_id):
    """Step 5: Download the final model."""
    model_url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/get_3d_model/single_head')
    headers = _get_api_headers(api_key)
    
    print(f"--- Step 5: Downloading 3D model ---")
    response = requests.get(model_url, headers=headers, stream=True)
    
    if response.status_code != 200:
        print(f"ERROR - Download Status: {response.status_code}")
        print(f"ERROR - Download Response: {response.text}")
        raise PipelineError(f"Download failed: {response.status_code} - {response.text}")
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".obj") as temp_file:
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
            total_size += len(chunk)
        temp_file_path = temp_file.name
    
    print(f"Downloaded {total_size} bytes to temporary file")
    
    # Save to Django model
    try:
        with open(temp_file_path, 'rb') as f:
            scan.processed_3d_model.save(f"{scan.id}_reconstructed.obj", File(f))
        print("--- Model saved successfully to database ---")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def _measure_mesh(scan):
    """Step 6: Perform measurements on the mesh."""
    print("--- Step 6: Measuring mesh ---")
    
    if not scan.processed_3d_model:
        raise PipelineError("Processed 3D model not found for measurement.")
    
    # Read the model into a temporary file
    with tempfile.NamedTemporaryFile(suffix=".obj", delete=False) as tmp:
        scan.processed_3d_model.seek(0)  # Ensure we're at the start of the file
        tmp.write(scan.processed_3d_model.read())
        mesh_path = tmp.name
    
    try:
        mesh = trimesh.load(mesh_path, force='mesh')
        print(f"Loaded mesh with {len(mesh.vertices)} vertices and {len(mesh.faces)} faces")
        
        measurements = perform_all_measurements(mesh)
        print(f"--- Measurements completed: {len(measurements)} measurements ---")
        
        return measurements
    except Exception as e:
        print(f"ERROR - Measurement failed: {str(e)}")
        raise PipelineError(f"Mesh measurement failed: {str(e)}")
    finally:
        if os.path.exists(mesh_path):
            os.remove(mesh_path)

def run_full_scan_pipeline(scan_id):
    """
    Main pipeline function that orchestrates the entire 3D reconstruction process.
    
    Steps:
    1. Initialize avatar with KeenTools API
    2. Upload photo to S3
    3. Start reconstruction job
    4. Poll for completion
    5. Download resulting 3D model
    6. Perform measurements on the mesh
    """
    from scans.models import Scan
    
    print(f"\n{'='*60}")
    print(f"Starting pipeline for scan ID: {scan_id}")
    print(f"{'='*60}\n")
    
    # Get the scan object
    try:
        scan = Scan.objects.get(id=scan_id)
        print(f"Found scan: {scan}")
    except Scan.DoesNotExist:
        raise PipelineError(f"Scan with ID {scan_id} not found")
    
    # Get and validate API key
    api_key = os.getenv('KEENTOOLS_SECRET_KEY')
    if not api_key:
        raise PipelineError("KEENTOOLS_SECRET_KEY environment variable is not set.")
    
    # Validate and clean the API key
    api_key = api_key.strip()  # Remove any whitespace
    
    # Check for common issues
    if '\n' in api_key or '\r' in api_key:
        print("WARNING: API key contains newline characters. Removing them...")
        api_key = api_key.replace('\n', '').replace('\r', '')
    
    if len(api_key) < 10:
        raise PipelineError(f"API key seems too short (length: {len(api_key)}). Please verify KEENTOOLS_SECRET_KEY.")
    
    print(f"API Key loaded (length: {len(api_key)})")
    print(f"API Key starts with: {api_key[:10]}")
    print(f"API Key ends with: {api_key[-10:]}")
    
    # Validate image exists
    if not scan.image_front:
        raise PipelineError("No front image found for this scan")
    
    if not os.path.exists(scan.image_front.path):
        raise PipelineError(f"Image file not found at: {scan.image_front.path}")
    
    print(f"Image found at: {scan.image_front.path}")
    
    try:
        # Execute pipeline steps
        avatar_id, upload_url = _init_avatar(api_key)
        _upload_photo(upload_url, scan.image_front.path)
        _start_reconstruction(api_key, avatar_id)
        _poll_for_completion(api_key, avatar_id)
        _download_and_save_model(scan, api_key, avatar_id)
        measurements = _measure_mesh(scan)
        
        print(f"\n{'='*60}")
        print(f"Pipeline completed successfully!")
        print(f"{'='*60}\n")
        
        return {"measurements": measurements, "avatar_id": avatar_id}
        
    except PipelineError as e:
        print(f"\n{'='*60}")
        print(f"Pipeline failed: {str(e)}")
        print(f"{'='*60}\n")
        raise
    except Exception as e:
        import traceback
        print(f"\n{'='*60}")
        print(f"Unexpected error in pipeline:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        raise PipelineError(f"Pipeline execution failed: {str(e)}")