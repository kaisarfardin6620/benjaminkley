from .reconstruction import generate_head_model
from .measurement import get_surface_measurements_from_model

def run_full_scan_pipeline(scan) -> dict:
    reconstruction_results = generate_head_model(
        image_paths={...},
        scan_id=str(scan.id)
    )
    
    model_file_path = reconstruction_results['output_model_absolute_path']
    gender = reconstruction_results['gender']

    measurement_results = get_surface_measurements_from_model(
        model_path=model_file_path,
        gender=gender,
        front_image_path=scan.image_front.path 
    )
    
    final_results = {
        "measurements": measurement_results,
        "reconstruction": reconstruction_results
    }
    
    return final_results