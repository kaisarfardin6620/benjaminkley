# scans/tasks.py

from celery import shared_task
from .models import Scan
from .processing.pipeline import run_full_scan_pipeline
import traceback

@shared_task
def process_scan_task(scan_id: str):
    """
    The background task that runs the entire AI pipeline.
    It handles success and failure and updates the database.
    """
    try:
        scan = Scan.objects.get(id=scan_id)
        
        # Run the entire AI pipeline
        results = run_full_scan_pipeline(scan)
        
        measurements = results.get('measurements', {})
        reconstruction = results.get('reconstruction', {})
        
        # Save all measurements to the database (in cm)
        for key, value in measurements.items():
            if hasattr(scan, key):
                setattr(scan, key, float(value) / 10.0)
        
        scan.processed_3d_model.name = reconstruction.get('output_model_relative_path')
        scan.status = Scan.Status.COMPLETED

    except Exception as e:
        # If anything goes wrong, mark the scan as FAILED
        error_message = str(e)
        print(f"CRITICAL ERROR processing scan {scan_id}: {error_message}")
        traceback.print_exc()
        
        # It's important to re-fetch the object in the except block
        scan = Scan.objects.get(id=scan_id)
        scan.status = Scan.Status.FAILED
        scan.failure_reason = error_message
    
    finally:
        # Always save the final state, whether success or failure
        scan.save()