from celery import shared_task
from .models import Scan
from .processing.pipeline import run_full_scan_pipeline

@shared_task(bind=True, max_retries=1) # bind=True allows access to `self`
def process_scan_task(self, scan_id: str):
    """
    Celery background task that executes the full AI pipeline.
    It handles success and failure cases, updating the Scan object in the database.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        results = run_full_scan_pipeline(scan)
        
        # On success, populate the model with estimated mm, converted to cm
        scan.eye_to_eye = results['measurements']['eye_to_eye'] / 10
        scan.ear_to_ear = results['measurements']['ear_to_ear'] / 10
        scan.head_height = results['measurements']['head_height'] / 10
        scan.head_width = results['measurements']['head_width'] / 10
        scan.head_length = results['measurements']['head_height'] / 10 # Approximation

        # Log the calibration data for traceability
        scan.calibration_method = results['measurements']['calibration_method']
        scan.assumed_ipd_mm = results['measurements']['assumed_ipd_mm']
        scan.calculated_pixels_per_mm = results['measurements']['calculated_pixels_per_mm']
        
        scan.processed_3d_model.name = results['reconstruction']['output_model_relative_path']
        scan.status = Scan.Status.COMPLETED
        
    except Exception as e:
        error_message = str(e)
        print(f"CRITICAL ERROR processing scan {scan_id} on try {self.request.retries}: {error_message}")
        
        # It is crucial to re-fetch the object within the except block
        scan = Scan.objects.get(id=scan_id)
        scan.status = Scan.Status.FAILED
        scan.failure_reason = error_message
        
    finally:
        scan.save() 

