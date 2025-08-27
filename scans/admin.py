from django.contrib import admin
from .models import Scan
from django.db import models

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin): 
    list_display = (
        'name',
        'user',
        'status',
        'created_at',
        'updated_at'
    )
    
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'user__username', 'id__iexact')
    
    fieldsets = (
        ('Scan Details', {
            'fields': ('id', 'name', 'user', 'status', 'failure_reason')
        }),
        ('User Inputs', {
            'fields': ('notes', 'custom_field', 'image_front', 'image_back', 'image_left', 'image_right')
        }),
        ('Final Measurements (cm)', {
            'fields': (
                'eye_to_eye', 'ear_to_ear', 'head_width', 'head_height',
                'head_circumference_A', 'forehead_to_back_B', 'cross_measurement_C', 'under_chin_D',
                'eyebrow_to_earlobe_E', 'eye_corner_to_ear_F', 'ear_height_G', 'ear_width_H',
                'cheek_guard_clearance_L', 'cheek_guard_height_M', 'cheek_guard_width_N'
            )
        }),
        ('Output Files', {
            'fields': ('processed_3d_model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    readonly_fields = ('id', 'user', 'created_at', 'updated_at', 'processed_3d_model', 'failure_reason') + \
                      tuple(f.name for f in Scan._meta.get_fields() if isinstance(f, models.DecimalField))

    def has_add_permission(self, request):
        return False