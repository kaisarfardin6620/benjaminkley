# scans/admin.py

from django.contrib import admin
from .models import Scan

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the Scan model.
    Provides a detailed, read-only view of each scan's inputs,
    processing state, and final results for traceability and review.
    """
    list_display = (
        'name',
        'user',
        'status',
        'created_at',
        'updated_at'
    )
    
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'user__username', 'id__iexact')
    
    # Organize the detail view into sections
    fieldsets = (
        ('Scan Details', {
            'fields': ('id', 'name', 'user', 'status', 'failure_reason')
        }),
        ('User Inputs', {
            'fields': ('notes', 'custom_field', 'image_front', 'image_back', 'image_left', 'image_right')
        }),
        ('Processing & Calibration Logs (Traceability)', {
            'fields': ('calibration_method', 'assumed_ipd_mm', 'calculated_pixels_per_mm')
        }),
        ('Final Estimated Measurements (cm)', {
            'fields': ('head_width', 'head_length', 'ear_to_ear', 'eye_to_eye')
        }),
        ('Output Files', {
            'fields': ('processed_3d_model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    # Make fields read-only to prevent accidental modification of results
    readonly_fields = (
        'id', 'user', 'created_at', 'updated_at', 'calibration_method',
        'assumed_ipd_mm', 'calculated_pixels_per_mm', 'head_width',
        'head_length', 'ear_to_ear', 'eye_to_eye', 'processed_3d_model',
        'failure_reason'
    )

    def has_add_permission(self, request):
        # Scans should only be created via the API, not the admin panel
        return False