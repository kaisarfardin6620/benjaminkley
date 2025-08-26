from .reconstruction import generate_head_model
from .measurement import get_surface_measurements_from_model

def run_full_scan_pipeline(scan) -> dict:
    print(f"Starting AI pipeline for scan ID: {scan.id}")

    reconstruction_results = generate_head_model(
        image_paths={'front': scan.image_front.path, 'back': scan.image_back.path,
                     'left': scan.image_left.path, 'right': scan.image_right.path},
        scan_id=str(scan.id)
    )
    
    model_file_path = reconstruction_results['output_model_absolute_path']
    gender = reconstruction_results['gender']

    measurement_results = get_surface_measurements_from_model(
        model_path=model_file_path,
        gender=gender
    )
    
    final_results = {
        "measurements": measurement_results,
        "reconstruction": reconstruction_results
    }
    
    print(f"Pipeline finished successfully for scan ID: {scan.id}")
    return final_results