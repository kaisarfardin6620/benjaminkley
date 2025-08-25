# scans/serializers.py

from rest_framework import serializers
from .models import Scan

class ScanCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for the initial upload of a new scan.
    Validates that the user has provided all required info and four images.
    """
    class Meta:
        model = Scan
        fields = (
            'name', 'notes', 'custom_field',
            'image_front', 'image_back', 'image_left', 'image_right'
        )

class ScanDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying the details of a scan.
    This is what the mobile app will receive when it checks the status or views results.
    """
    class Meta:
        model = Scan
        # Includes all relevant fields for the "My Scan View Details" screen.
        fields = (
            'id', 'name', 'notes', 'custom_field', 'status',
            'created_at', 'processed_3d_model', 'failure_reason',
            # Measurements are returned in cm as per the model definition
            'head_width', 'head_length', 'ear_to_ear', 'eye_to_eye'
        )