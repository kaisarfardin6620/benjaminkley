from celery import shared_task
from .models import Scan
from .processing.pipeline import run_full_scan_pipeline
import traceback

@shared_task
def process_scan_and_save(scan_id):
    print("--- RUNNING THE FINAL DIAGNOSTIC TASK ---")

    scan = Scan.objects.get(id=scan_id)
    
    results = run_full_scan_pipeline(scan)
    
    measurements = results.get('measurements', {})
    
    for key, value in measurements.items():
        if hasattr(scan, key) and value is not None:
            setattr(scan, key, float(value) / 10.0) 
    
    scan.status = Scan.Status.COMPLETED
    
    scan.save()