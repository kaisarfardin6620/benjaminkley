from .reconstruction import generate_head_model_locally
from .measurement import get_surface_measurements_from_model, MeasurementError
from .gender_predictor import predict_gender
from django.core.files import File
import os
import traceback

class PipelineError(Exception):
    """Custom exception for pipeline failures."""
    pass

def run_full_scan_pipeline(scan) -> dict:
    """
    Runs the full processing pipeline for a scan, with improved error handling.
    """
    try:
        image_paths = {
            "front": scan.image_front.path,
            "back": scan.image_back.path,
            "left": scan.image_left.path,
            "right": scan.image_right.path,
        }
        
        # Log to indicate the start of the process
        print("Pipeline Step 1: Predicting gender...")
        gender = predict_gender(scan.image_front.path)
        print(f"Predicted gender: {gender}")

        # Log to indicate the start of the 3D model generation
        print("Pipeline Step 2: Generating 3D model...")
        local_model_path, output_filename = generate_head_model_locally(
            image_paths=image_paths,
            scan_id=str(scan.id),
            gender=gender
        )

        if not local_model_path:
            raise PipelineError("3D model reconstruction failed. Model path is None.")
        
        # Log to indicate the start of the measurement calculation
        print("Pipeline Step 3: Calculating measurements...")
        try:
            measurement_results = get_surface_measurements_from_model(
                model_path=local_model_path,
                gender=gender,
                front_image_path=scan.image_front.path
            )
        except MeasurementError as me:
            print(f"Error during measurement calculation: {me}")
            raise PipelineError(f"Measurement step failed: {me}")
        
        if not measurement_results:
            raise PipelineError("Measurement calculation failed. Returned empty results.")
        
        # Log to indicate the start of the cloud storage step
        print("Pipeline Step 4: Saving 3D model to cloud storage...")
        with open(local_model_path, 'rb') as f:
            cloud_path = f"scans/outputs/{output_filename}"
            scan.processed_3d_model.save(cloud_path, File(f))
        
        # Log cleanup step
        print("Pipeline Step 5: Cleaning up local temporary file...")
        os.remove(local_model_path)
        print("Local file cleaned up successfully.")

        # Final log message before returning
        print("Pipeline completed successfully. Returning measurements.")
        return {"measurements": measurement_results}

    except Exception as e:
        # Catch any pipeline-specific errors and re-raise them with context
        print(f"Error in pipeline for scan {scan.id}: {e}")
        traceback.print_exc()
        raise PipelineError(f"Pipeline execution failed: {e}")
