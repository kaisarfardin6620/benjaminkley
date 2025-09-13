# scans/tasks.py
from celery import shared_task
import logging
from .models import Scan
from .processing.pipeline import run_full_scan_pipeline, PipelineError

logger = logging.getLogger(__name__)

@shared_task
def process_scan_and_save(scan_id: str):
    logger.info(f"Starting processing for scan {scan_id}")
    scan = Scan.objects.get(id=scan_id)
    try:
        results = run_full_scan_pipeline(scan)
        measurements = results.get('measurements', {})
        
        # Update measurements (convert to Decimal as per model)
        from decimal import Decimal
        scan.head_width = Decimal(measurements.get('head_width', 0))
        scan.head_length = Decimal(measurements.get('head_length', 0))
        scan.ear_to_ear = Decimal(measurements.get('ear_to_ear', 0))
        scan.eye_to_eye = Decimal(measurements.get('eye_to_eye', 0))
        
        scan.status = Scan.Status.COMPLETED
        logger.info(f"Completed processing for scan {scan_id}")
    except (PipelineError, Exception) as e:
        scan.status = Scan.Status.FAILED
        scan.failure_reason = str(e)
        logger.error(f"Failed processing for scan {scan_id}: {e}")
    finally:
        scan.save()  # Always save, even on failure