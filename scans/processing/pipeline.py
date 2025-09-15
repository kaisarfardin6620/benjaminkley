from .reconstruction import generate_head_model_locally
from .measurement import get_measurements_from_images, get_surface_measurements_from_model, MeasurementError
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

        print("Pipeline Step 2: Calculating initial measurements from 2D images...")
        initial_measurements = get_measurements_from_images(image_paths)
        if not initial_measurements:
            raise PipelineError("Initial 2D measurement calculation failed.")

        print("Pipeline Step 3: Generating reshaped 3D model...")
        local_model_path, output_filename = generate_head_model_locally(
            scan_id=str(scan.id),
            gender=gender,
            measurements=initial_measurements
        )
        if not local_model_path:
            raise PipelineError("3D model reconstruction failed.")
        
        print("Pipeline Step 4: Refining measurements with the 3D model...")
        final_measurements = get_surface_measurements_from_model(
            model_path=local_model_path,
            initial_measurements=initial_measurements
        )
        if not final_measurements:
            raise PipelineError("Measurement refinement with 3D model failed.")
        
        print("Pipeline Step 5: Saving 3D model to cloud storage...")
        with open(local_model_path, 'rb') as f:
            scan.processed_3d_model.save(output_filename, File(f), save=False)
        
        print("Pipeline Step 6: Cleaning up local temporary file...")
        os.remove(local_model_path)
        print("Local file cleaned up successfully.")

        print("Pipeline completed successfully.")
        return {"measurements": final_measurements}

    except (MeasurementError, ValueError, Exception) as e:
        print(f"Error in pipeline for scan {scan.id}: {e}")
        traceback.print_exc()
        raise PipelineError(f"Pipeline execution failed: {e}")