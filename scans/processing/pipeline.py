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
    """Returns the standard Authorization header."""
    return {'Authorization': f'Bearer {api_key}'}

def _init_avatar(api_key):
    """Step 1: Initialize the avatar."""
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, 'avatar/init')
    headers = _get_api_headers(api_key)
    payload = {"photos_count": 1}

    print(f"--- Step 1: POST to {url} ---")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise PipelineError(f"Init failed: {response.status_code} - {response.text}")
    
    data = response.json()
    avatar_id = data.get('avatar_id')
    upload_url = data.get('presigned_urls', [{}])[0].get('url')
    if not avatar_id or not upload_url:
        raise PipelineError("Invalid init response.")
    
    print(f"--- Avatar initialized. ID: {avatar_id} ---")
    return avatar_id, upload_url

def _upload_photo(upload_url, image_path):
    """Step 2: Upload photo to S3."""
    print(f"--- Step 2: PUT to S3 URL ---")
    with open(image_path, 'rb') as f:
        headers = {'Content-Type': 'image/jpeg'}
        response = requests.put(upload_url, headers=headers, data=f)
        if response.status_code != 200: raise PipelineError(f"S3 upload failed: {response.status_code} - {response.text}")
    print("--- Photo uploaded. ---")

def _start_reconstruction(api_key, avatar_id):
    """Step 3: Start reconstruction."""
    url = os.path.join(settings.KEENTOOLS_API_BASE_URL, f'avatar/{avatar_id}/create')
    headers = _get_api_headers(api_key)
    print(f"--- Step 3: POST to {url} ---")
    response = requests.post(url, headers=headers)
    if response.status_code != 200: raise PipelineError(f"Start reconstruction failed: {response.status_code} - {response.text}")
    print("--- Reconstruction started. ---")

def _poll_for_completion(api_key, avatar_id, timeout=300):
    """Step 4: Check job status."""
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".obj") as temp_file:
        for chunk in response.iter_content(chunk_size=8192): temp_file.write(chunk)
        temp_file_path = temp_file.name
    with open(temp_file_path, 'rb') as f:
        scan.processed_3d_model.save(f"{scan.id}_reconstructed.obj", File(f))
    os.remove(temp_file_path)
    print("--- Final model saved. ---")

def _measure_mesh(scan):
    if not scan.processed_3d_model: raise PipelineError("Model not found for measurement.")
    with tempfile.NamedTemporaryFile(suffix=".obj", delete=False) as tmp:
        tmp.write(scan.processed_3d_model.read())
        mesh_path = tmp.name
    try:
        mesh = trimesh.load(mesh_path, force='mesh')
        return perform_all_measurements(mesh)
    finally:
        os.remove(mesh_path)

def run_full_scan_pipeline(scan_id):
    from scans.models import Scan
    scan = Scan.objects.get(id=scan_id)
    api_key = os.getenv('KEENTOOLS_SECRET_KEY') 
    if not api_key: raise PipelineError("KEENTOOLS_SECRET_KEY is not set.")
    try:
        avatar_id, upload_url = _init_avatar(api_key)
        _upload_photo(upload_url, scan.image_front.path)
        _start_reconstruction(api_key, avatar_id)
        _poll_for_completion(api_key, avatar_id)
        _download_and_save_model(scan, api_key, avatar_id)
        measurements = _measure_mesh(scan)
        return {"measurements": measurements}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise PipelineError(f"Pipeline execution failed: {e}")