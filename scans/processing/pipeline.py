from .reconstruction import generate_head_model_locally
from .measurement import get_surface_measurements_from_model
from .gender_predictor import predict_gender
from django.core.files import File
import os

def run_full_scan_pipeline(scan) -> dict:
    image_paths = {
        "front": scan.image_front.path,
        "back": scan.image_back.path,
        "left": scan.image_left.path,
        "right": scan.image_right.path,
    }
    gender = predict_gender(scan.image_front.path)

    local_model_path, output_filename = generate_head_model_locally(
        image_paths=image_paths,
        scan_id=str(scan.id),
        gender=gender
    )

    measurement_results = get_surface_measurements_from_model(
        model_path=local_model_path,
        gender=gender,
        front_image_path=scan.image_front.path
    )

    with open(local_model_path, 'rb') as f:
        cloud_path = f"scans/outputs/{output_filename}"
        scan.processed_3d_model.save(cloud_path, File(f))
    
    os.remove(local_model_path)

    return {"measurements": measurement_results}