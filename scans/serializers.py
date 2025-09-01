# scans/serializers.py

from rest_framework import serializers
from .models import Scan

class ScanCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for the initial upload of a new scan.
    """
    class Meta:
        model = Scan
        fields = ('name', 'notes', 'custom_field', 'image_front', 'image_back', 'image_left', 'image_right')


class ScanDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying the final details of a scan TO THE MOBILE APP.
    This version produces the exact fields required by the UI screenshot, plus the status.
    """
    Name = serializers.SerializerMethodField()
    Date_of_Scan = serializers.DateTimeField(source='created_at', format="%B %d, %Y", read_only=True)

    Head_Width = serializers.CharField(source='head_width')
    Head_Length = serializers.CharField(source='head_length')
    Ear_to_Ear = serializers.CharField(source='ear_to_ear')
    Eye_to_Eye = serializers.CharField(source='eye_to_eye')
    Notes = serializers.CharField(source='notes')
    Custom_Fit = serializers.CharField(source='custom_field')
    
    # --- THIS IS THE FIX ---
    # The 'status' field has now been added.
    status = serializers.CharField()

    class Meta:
        model = Scan
        # The fields list now contains the status field.
        fields = (
            'Name',
            'Date_of_Scan',
            'status', # The mobile app needs this field
            'Head_Width',
            'Head_Length',
            'Ear_to_Ear',
            'Eye_to_Eye',
            'Notes',
            'Custom_Fit',
        )
        
    def get_Name(self, obj):
        if obj.user:
            return obj.user.get_full_name()
        return "N/A"