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
    This version produces the exact fields required by the UI screenshot.
    """
    # Create a custom field 'Name' that gets the user's full name.
    Name = serializers.SerializerMethodField()
    
    # --- START OF THE FIX ---
    # Create 'Date of Scan' and format it beautifully to match the UI.
    # Changed "%-d" to "%d" to ensure compatibility with Windows.
    Date_of_Scan = serializers.DateTimeField(source='created_at', format="%B %d, %Y", read_only=True)
    # --- END OF THE FIX ---

    # Rename the measurement and note fields to match the UI labels exactly.
    Head_Width = serializers.CharField(source='head_width')
    Head_Length = serializers.CharField(source='head_length')
    Ear_to_Ear = serializers.CharField(source='ear_to_ear')
    Eye_to_Eye = serializers.CharField(source='eye_to_eye')
    Notes = serializers.CharField(source='notes')
    Custom_Fit = serializers.CharField(source='custom_field')

    class Meta:
        model = Scan
        # The fields list now contains ONLY the fields visible in the screenshot.
        fields = (
            'Name',
            'Date_of_Scan',
            'Head_Width',
            'Head_Length',
            'Ear_to_Ear',
            'Eye_to_Eye',
            'Notes',
            'Custom_Fit',
        )
        
    def get_Name(self, obj):
        """
        This custom method provides the data for the 'Name' field.
        It gets the full name from the related User object.
        """
        if obj.user:
            return obj.user.get_full_name()
        return "N/A"