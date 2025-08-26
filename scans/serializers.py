from rest_framework import serializers
from .models import Scan

class ScanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ('name', 'notes', 'custom_field', 'image_front', 'image_back', 'image_left', 'image_right')

class ScanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = (
            'id', 'name', 'notes', 'custom_field', 'status',
            'created_at', 'failure_reason',
            'head_circumference_A',
            'forehead_to_back_B',
            'cross_measurement_C',
            'under_chin_D',
        )