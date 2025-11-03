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
    return {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

def _make_url(path: str) -> str:
    base = settings.KEENTOOLS_API_BASE_URL.rstrip('/') + '/'
    return os.path.join(base, path)

def _init_avatar(api_key, img_count):
    url = _make_url("avatar/init") 
    headers = _get_api_headers(api_key)
    payload = {"img_count": img_count}

    print(f"--- Step 1: POST to {url} ---")
    response = requests.post(url, headers=headers, json=payload, timeout=15)

    if response.status_code != 200:
        raise PipelineError(f"Init failed: {response.status_code} - {response.text}")
    
    data = response.json()
    avatar_id = data.get("avatar_id")
    presigned_urls = data.get("img_urls")
    
    if not avatar_id or len(presigned_urls) != img_count:
        raise PipelineError(f"Invalid init response. Expected {img_count} URLs, got {len(presigned_urls)}.")
    
    print(f"--- Avatar initialized. ID: {avatar_id} ---")
    return avatar_id, presigned_urls

def _upload_photo(image_path, upload_url):
    print(f"--- Step 2: PUT to S3 URL for {os.path.basename(image_path)} ---")
    if not os.path.exists(image_path):
        raise PipelineError(f"Local image file not found at: {image_path}")

    with open(image_path, 'rb') as f:
        img_data = f.read()
    
    res = requests.put(upload_url, data=img_data, headers={"Content-Type": "image/jpeg"}, timeout=30) 
    
    if res.status_code not in [200, 201]: 
        raise PipelineError(f"S3 upload failed: {res.status_code} - {res.text}")
    print("--- Photo uploaded successfully. ---")

def _start_reconstruction(api_key, avatar_id):
    url = _make_url(f"avatar/{avatar_id}/create")
    headers = _get_api_headers(api_key)
    
    payload = {
        "focal_length_type": "estimate_common", 
        "expressions_enabled": False
    }

    print(f"--- Step 3: POST to {url} with payload ---")
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if response.status_code != 200: 
        raise PipelineError(f"Start reconstruction failed: {response.status_code} - {response.text}")
    print("--- Reconstruction started. ---")

def _poll_for_completion(api_key, avatar_id, timeout=300):
    status_url = _make_url(f"avatar/{avatar_id}/get_status")
    headers = _get_api_headers(api_key)
    start_time = time.time()
    print(f"--- Step 4: Polling {status_url} ---")
    
    while time.time() - start_time < timeout:
        response = requests.get(status_url, headers=headers, timeout=15)
        if response.status_code != 200: 
            raise PipelineError(f"Polling failed: {response.status_code} - {response.text}")
        
        data = response.json()
        status = data.get('status')
        print(f"Job status: {status}")
        
        if status == 'completed':
            print("--- Job completed. ---")
            return
        elif status == 'failed':
            error_msg = data.get('data', {}).get('error', 'Unknown error during reconstruction.')
            raise PipelineError(f"KeenTools job failed: {error_msg}")
            
        time.sleep(10)
        
    raise PipelineError("Job timed out.")

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
        from ..mesh_measurements import perform_all_measurements
        return perform_all_measurements(mesh)
    finally:
        if mesh_path and os.path.exists(mesh_path):
            os.remove(mesh_path)

def _download_and_save_model(scan, api_key, avatar_id):
    model_url = _make_url(f'avatar/{avatar_id}/get_3d_model/single_head') 
    headers = _get_api_headers(api_key)
    print(f"--- Step 5: GET from {model_url} ---")
    response = requests.get(model_url, headers=headers, stream=True, timeout=60)
    if response.status_code != 200: raise PipelineError(f"Download failed: {response.status_code} - {response.text}")
    
    temp_file_path = None 
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".obj") as temp_file:
        for chunk in response.iter_content(chunk_size=8192): temp_file.write(chunk)
        temp_file_path = temp_file.name
    
    with open(temp_file_path, 'rb') as f:
        scan.processed_3d_model.save(f"{scan.id}_reconstructed.obj", File(f), save=False)
    
    print("--- Final model saved to FileField. ---")
    return temp_file_path

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

    try:
        image_count = len(image_paths)
        avatar_id, upload_urls = _init_avatar(api_key, image_count)
        
        for path, url in zip(image_paths, upload_urls):
            _upload_photo(path, url)
            
        _start_reconstruction(api_key, avatar_id)
        _poll_for_completion(api_key, avatar_id)
        
        temp_file_path = _download_and_save_model(scan, api_key, avatar_id)

        mesh = trimesh.load(temp_file_path, file_type='obj', force='mesh')
        from ..mesh_measurements import perform_all_measurements
        measurements = perform_all_measurements(mesh)
        
        return {"measurements": measurements}
        
    except Exception as e:
        import traceback
        traceback.print_exc()

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        raise PipelineError(f"Pipeline execution failed: {e}")