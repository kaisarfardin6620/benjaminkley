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
    Adds "cm" suffix to measurements for frontend display.
    """
    head_width = serializers.SerializerMethodField()
    head_length = serializers.SerializerMethodField()
    ear_to_ear = serializers.SerializerMethodField()
    eye_to_eye = serializers.SerializerMethodField()

    class Meta:
        model = Scan
        fields = (
            'id', 'name', 'notes', 'custom_field', 'status',
            'created_at', 'processed_3d_model', 'failure_reason',
            'head_width', 'head_length', 'ear_to_ear', 'eye_to_eye'
        )

    def get_head_width(self, obj):
        return f"{obj.head_width:.2f} cm" if obj.head_width is not None else None

    def get_head_length(self, obj):
        return f"{obj.head_length:.2f} cm" if obj.head_length is not None else None

    def get_ear_to_ear(self, obj):
        return f"{obj.ear_to_ear:.2f} cm" if obj.ear_to_ear is not None else None

    def get_eye_to_eye(self, obj):
        return f"{obj.eye_to_eye:.2f} cm" if obj.eye_to_eye is not None else None
