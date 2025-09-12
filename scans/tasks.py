from celery import shared_task
from .models import Scan
from .processing.pipeline import run_full_scan_pipeline
import traceback
from notifications.utils import create_and_send_notification
from dashboard.models import AdminNotification


@shared_task
def process_scan_and_save(scan_id: str):
    try:
        scan = Scan.objects.get(id=scan_id)

        AdminNotification.objects.create(
            message=f"User {scan.user.get_full_name()} has submitted a new scan for processing: '{scan.name}'."
        )

        print(f"--- Starting processing for scan {scan_id} ---")
        
        results = run_full_scan_pipeline(scan)
        measurements = results.get('measurements', {})
        
        for key, value in measurements.items():
            if hasattr(scan, key) and value is not None:
                setattr(scan, key, float(value) / 10.0) 
        
        scan.status = Scan.Status.COMPLETED
        print(f"--- Successfully completed scan {scan_id} ---")

    except Exception as e:
        error_message = str(e)
        print(f"--- CRITICAL ERROR processing scan {scan_id}: {error_message} ---")
        traceback.print_exc()  

        scan = Scan.objects.get(id=scan_id)
        scan.status = Scan.Status.FAILED
        scan.failure_reason = error_message

    finally:
        scan.save()
        print(f"--- Final state for scan {scan_id} saved. Status: {scan.status} ---")

        if scan.status == Scan.Status.COMPLETED:
            create_and_send_notification(
                user=scan.user,
                title="Scan Completed",
                message=f"Your scan '{scan.name}' has been successfully processed."
            )
        elif scan.status == Scan.Status.FAILED:
            create_and_send_notification(
                user=scan.user,
                title="Scan Failed",
                message=f"There was an error processing your scan '{scan.name}'. Please try again or contact support."
            )