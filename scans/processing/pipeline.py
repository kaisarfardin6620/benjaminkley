# scans/processing/pipeline.py

from .reconstruction import generate_head_model
from .measurement import get_surface_measurements_from_model
from .gender_predictor import predict_gender

def run_full_scan_pipeline(scan) -> dict:
    
    image_paths = {
        "front": scan.image_front.path,
        "back": scan.image_back.path,
        "left": scan.image_left.path,
        "right": scan.image_right.path,
    }

    reconstruction_results = generate_head_model(
        image_paths=image_paths,
        scan_id=str(scan.id)
    )
    
    model_file_path = reconstruction_results['output_model_absolute_path']
    
    gender = predict_gender(scan.image_front.path)

    measurement_results = get_surface_measurements_from_model(
        model_path=model_file_path,
        gender=gender,
        front_image_path=scan.image_front.path 
    )
    
    reconstruction_results['gender'] = gender
    
    final_results = {
        "measurements": measurement_results,
        "reconstruction": reconstruction_results
    }
    
    return final_results