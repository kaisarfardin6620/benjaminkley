from django.contrib import admin
from .models import Scan

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
        ('Final Surface Measurements (cm)', {
            'fields': (
                'head_circumference_A',
                'forehead_to_back_B',
                'cross_measurement_C',
                'under_chin_D'
            )
        }),
        ('Output Files', {
            'fields': ('processed_3d_model',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    readonly_fields = (
        'id', 'user', 'created_at', 'updated_at', 'processed_3d_model',
        'failure_reason', 'head_circumference_A', 'forehead_to_back_B',
        'cross_measurement_C', 'under_chin_D'
    )

    def has_add_permission(self, request):
        return False