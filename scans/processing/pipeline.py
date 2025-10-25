import requests
import time
import os
import tempfile
import trimesh
from django.conf import settings
from django.core.files import File
from ..mesh_measurements import perform_all_measurements
import traceback

class PipelineError(Exception):
    pass

def _get_api_headers(api_key):
    return {'Authorization': f'Bearer {api_key}'}

def _init_avatar(api_key):
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, 'avatar/init')
    headers = _get_api_headers(api_key)
    payload = {"photos_count": 4}

    print(f"--- Step 1: POST to {url} ---")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise PipelineError(f"Init failed: {response.status_code} - {response.text}")
    
    data = response.json()
    avatar_id = data.get('avatar_id')
    presigned_urls = [p.get('url') for p in data.get('presigned_urls', [{}])]
    
    if not avatar_id or len(presigned_urls) != 4:
        raise PipelineError(f"Invalid init response. Expected 4 URLs, got {len(presigned_urls)}.")
    
    print(f"--- Avatar initialized. ID: {avatar_id} with 4 upload URLs ---")
    return avatar_id, presigned_urls

def _upload_photo(upload_url, image_path):
    print(f"--- Step 2: PUT to S3 URL for {os.path.basename(image_path)} ---")
    if not os.path.exists(image_path):
        raise PipelineError(f"Local image file not found at: {image_path}")

    with open(image_path, 'rb') as f:
        headers = {'Content-Type': 'image/jpeg'} 
        response = requests.put(upload_url, headers=headers, data=f)
        if response.status_code != 200: raise PipelineError(f"S3 upload failed: {response.status_code} - {response.text}")
    print("--- Photo uploaded successfully. ---")

def _start_reconstruction(api_key, avatar_id):
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/create')
    headers = _get_api_headers(api_key)
    print(f"--- Step 3: POST to {url} ---")
    response = requests.post(url, headers=headers)
    if response.status_code != 200: raise PipelineError(f"Start reconstruction failed: {response.status_code} - {response.text}")
    print("--- Reconstruction started. ---")

def _poll_for_completion(api_key, avatar_id, timeout=300):
    status_url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/get_status')
    headers = _get_api_headers(api_key)
    start_time = time.time()
    print(f"--- Step 4: Polling {status_url} ---")
    while time.time() - start_time < timeout:
        response = requests.get(status_url, headers=headers)
        if response.status_code != 200: raise PipelineError(f"Polling failed: {response.status_code} - {response.text}")
        data = response.json()
        status = data.get('status')
        print(f"Job status: {status}")
        if status == 'completed':
            print("--- Job completed. ---")
            return
        elif status == 'failed':
            raise PipelineError(f"KeenTools job failed: {data.get('error', 'Unknown')}")
        time.sleep(15)
    raise PipelineError("Job timed out.")

def _download_and_save_model(scan, api_key, avatar_id):
    """Step 5: Download the final model."""
    model_url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/get_3d_model/single_head') 
    headers = _get_api_headers(api_key)
    print(f"--- Step 5: GET from {model_url} ---")
    response = requests.get(model_url, headers=headers, stream=True)
    if response.status_code != 200: raise PipelineError(f"Download failed: {response.status_code} - {response.text}")
    
    temp_file_path = None 
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".obj") as temp_file:
        for chunk in response.iter_content(chunk_size=8192): temp_file.write(chunk)
        temp_file_path = temp_file.name
    
    with open(temp_file_path, 'rb') as f:
        scan.processed_3d_model.save(f"{scan.id}_reconstructed.obj", File(f), save=False)
    
    os.remove(temp_file_path)
    print("--- Final model saved to FileField. ---")

def _measure_mesh(scan):
    if not scan.processed_3d_model: raise PipelineError("Model not found for measurement.")
    
    scan.processed_3d_model.seek(0) 
    
    mesh_path = None
    
    with tempfile.NamedTemporaryFile(suffix=".obj", delete=False) as tmp:
        for chunk in scan.processed_3d_model.chunks():
            tmp.write(chunk)
        mesh_path = tmp.name
        tmp.close()
    try:
        mesh = trimesh.load(mesh_path, file_type='obj', force='mesh')
        return perform_all_measurements(mesh)
    finally:
        if mesh_path and os.path.exists(mesh_path):
            os.remove(mesh_path)

def run_full_scan_pipeline(scan_id):
    from scans.models import Scan
    scan = Scan.objects.get(id=scan_id)
    
    api_key = getattr(settings, 'KEENTOOLS_SECRET_KEY', None)
    if not api_key: raise PipelineError("KEENTOOLS_SECRET_KEY is not set in Django settings.")
    
    image_paths = [
        scan.image_front.path,
        scan.image_back.path,
        scan.image_left.path,
        scan.image_right.path,
    ]
    
    temp_file_path = None 
    mesh_path = None

    try:
        avatar_id, upload_urls = _init_avatar(api_key)
        
        for url, path in zip(upload_urls, image_paths):
            _upload_photo(url, path)
            
        _start_reconstruction(api_key, avatar_id)
        _poll_for_completion(api_key, avatar_id)
        
        model_url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/get_3d_model/single_head')
        headers = _get_api_headers(api_key)
        response = requests.get(model_url, headers=headers, stream=True)
        if response.status_code != 200: raise PipelineError(f"Download failed: {response.status_code} - {response.text}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".obj") as temp_file:
            for chunk in response.iter_content(chunk_size=8192): temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        with open(temp_file_path, 'rb') as f:
            scan.processed_3d_model.save(f"{scan.id}_reconstructed.obj", File(f), save=False)
            
        mesh_path = temp_file_path
        
        try:
            mesh = trimesh.load(mesh_path, file_type='obj', force='mesh')
            measurements = perform_all_measurements(mesh)
        finally:
            if mesh_path and os.path.exists(mesh_path):
                os.remove(mesh_path)
                
        temp_file_path = None 
        
        return {"measurements": measurements}
        
    except Exception as e:
        import traceback
        traceback.print_exc()

        if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        if 'mesh_path' in locals() and mesh_path and os.path.exists(mesh_path):
            os.remove(mesh_path)
            
        raise PipelineError(f"Pipeline execution failed: {e}")