# scans/models.py

from django.db import models
from django.contrib.auth.models import User
import uuid

class Scan(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scans')

    # --- User-provided inputs from the "Input Info" screen ---
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    custom_field = models.CharField(max_length=255, blank=True, null=True)
    image_front = models.ImageField(upload_to='scans/inputs/')
    image_back = models.ImageField(upload_to='scans/inputs/')
    image_left = models.ImageField(upload_to='scans/inputs/')
    image_right = models.ImageField(upload_to='scans/inputs/')

    # --- Processing status and final outputs ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        help_text="The current processing status of the scan."
    )
    processed_3d_model = models.FileField(upload_to='scans/outputs/', null=True, blank=True)
    
    # --- Final Estimated Measurements (stored in cm) ---
    head_width = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    head_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ear_to_ear = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    eye_to_eye = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # --- Fields for logging the estimation process for safety and traceability ---
    calibration_method = models.CharField(max_length=50, null=True, blank=True)
    assumed_ipd_mm = models.FloatField(null=True, blank=True)
    calculated_pixels_per_mm = models.FloatField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True, help_text="Logs why a scan failed.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Scan"
        verbose_name_plural = "User Scans"

    def __str__(self):
        return f"Scan '{self.name}' for {self.user.username}"