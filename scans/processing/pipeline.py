from .reconstruction import generate_head_model_locally
from .measurement import get_surface_measurements_from_model, MeasurementError
from .gender_predictor import predict_gender
from django.core.files import File
import os
import traceback

class PipelineError(Exception):
    pass

def run_full_scan_pipeline(scan) -> dict:
    try:
        image_paths = {
            "front": scan.image_front.path,
            "back": scan.image_back.path,
            "left": scan.image_left.path,
            "right": scan.image_right.path,
        }
        
        print("Pipeline Step 1: Predicting gender...")
        gender = predict_gender(scan.image_front.path)
        print(f"Predicted gender: {gender}")

        print("Pipeline Step 2: Generating 3D model...")
        local_model_path, output_filename = generate_head_model_locally(
            image_paths=image_paths,
            scan_id=str(scan.id),
            gender=gender
        )

        if not local_model_path:
            raise PipelineError("3D model reconstruction failed. Model path is None.")
        
        print("Pipeline Step 3: Calculating measurements...")
        try:
            measurement_results = get_surface_measurements_from_model(
                model_path=local_model_path,
                gender=gender,
                front_image_path=scan.image_front.path,
                side_image_path=scan.image_left.path  
            )
        except MeasurementError as me:
            print(f"Error during measurement calculation: {me}")
            raise PipelineError(f"Measurement step failed: {me}")
        
        if not measurement_results:
            raise PipelineError("Measurement calculation failed. Returned empty results.")
        
        print("Pipeline Step 4: Saving 3D model to cloud storage...")
        with open(local_model_path, 'rb') as f:
            cloud_path = f"scans/outputs/{output_filename}"
            scan.processed_3d_model.save(cloud_path, File(f))
        
        print("Pipeline Step 5: Cleaning up local temporary file...")
        os.remove(local_model_path)
        print("Local file cleaned up successfully.")

        print("Pipeline completed successfully. Returning measurements.")
        return {"measurements": measurement_results}

    except Exception as e:
        print(f"Error in pipeline for scan {scan.id}: {e}")
        traceback.print_exc()
        raise PipelineError(f"Pipeline execution failed: {e}")