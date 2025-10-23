# scans/tasks.py

from celery import shared_task
import logging
from .processing.pipeline import run_full_scan_pipeline, PipelineError
from decimal import Decimal
from notifications.utils import create_and_send_notification
from dashboard.models import AdminNotification
from scans.models import Scan

logger = logging.getLogger(__name__)

@shared_task
def process_scan_and_save(scan_id: str):
    logger.info(f"Starting professional reconstruction for scan {scan_id}")
    scan = Scan.objects.get(id=scan_id)
    try:
        AdminNotification.objects.create(
            notification_type=AdminNotification.NotificationType.NEW_SCAN,
            message=f"User {scan.user.get_full_name()} submitted new scan: '{scan.name}'."
        )
        results = run_full_scan_pipeline(scan_id)
        measurements = results.get('measurements', {})
        
        # Iteratively save all new, accurate measurements to the database model
        for key, value in measurements.items():
            if hasattr(scan, key) and value is not None:
                setattr(scan, key, Decimal(f"{value:.2f}"))
        
        scan.status = Scan.Status.COMPLETED
        logger.info(f"Completed processing for scan {scan_id}")

    except (PipelineError, Exception) as e:
        scan.status = Scan.Status.FAILED
        scan.failure_reason = str(e)
        logger.error(f"Failed processing for scan {scan_id}: {e}")

    finally:
        scan.save()
        
        if scan.status == Scan.Status.COMPLETED:
            create_and_send_notification(user=scan.user, title="Scan Completed", message=f"Your scan '{scan.name}' has been successfully processed.")
        elif scan.status == Scan.STatus.FAILED:
            create_and_send_notification(user=scan.user, title="Scan Failed", message=f"There was an error processing your scan '{scan.name}'.")