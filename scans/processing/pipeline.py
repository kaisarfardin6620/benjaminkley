# scans/processing/pipeline.py

from .gender_predictor import predict_gender
from .measurement import get_measurements_from_image
from .reconstruction import generate_head_model

def run_full_scan_pipeline(scan) -> dict:
    """
    Orchestrates the AI pipeline: gender, estimation, validation, and reconstruction.

    Args:
        scan: The Django Scan model instance.

    Returns:
        A dictionary containing the final results.

    Raises:
        ValueError: If any step of the measurement and validation process fails.
    """
    print(f"Starting AI pipeline for scan ID: {scan.id}")

    # Step 1: Predict gender from the front-facing image.
    gender = predict_gender(image_path=scan.image_front.path)

    # Step 2: Get estimated and validated measurements. This can raise a ValueError.
    measurement_results = get_measurements_from_image(image_path=scan.image_front.path)
    
    # Step 3: Generate the 3D head model.
    reconstruction_results = generate_head_model(
        gender=gender,
        scan_id=str(scan.id),
        measurements=measurement_results
    )

    # Step 4: Combine all results for the Celery task.
    final_results = {
        "measurements": measurement_results,
        "reconstruction": reconstruction_results
    }
    
    print(f"Pipeline finished successfully for scan ID: {scan.id}")
    return final_results