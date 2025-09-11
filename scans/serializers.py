from rest_framework import serializers
from .models import Scan

class ScanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ('name', 'notes', 'custom_field', 'image_front', 'image_back', 'image_left', 'image_right')


class ScanDetailSerializer(serializers.ModelSerializer):
    Name = serializers.SerializerMethodField()
    Date_of_Scan = serializers.DateTimeField(source='created_at', format="%B %d, %Y", read_only=True)

    Head_Width = serializers.CharField(source='head_width')
    Head_Length = serializers.CharField(source='head_length')
    Ear_to_Ear = serializers.CharField(source='ear_to_ear')
    Eye_to_Eye = serializers.CharField(source='eye_to_eye')
    Notes = serializers.CharField(source='notes')
    Custom_Fit = serializers.CharField(source='custom_field')
    status = serializers.CharField()
    thumbnail_image = serializers.ImageField(source='image_front', use_url=True, read_only=True)
    scan_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = Scan
        fields = (
            'scan_id',
            'Name',
            'Date_of_Scan',
            'status',
            'thumbnail_image',
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