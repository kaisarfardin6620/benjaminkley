from rest_framework import serializers
from .models import Scan

class ScanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = (
            'name', 
            'notes', 
            'custom_field', 
            'image_front', 
            'image_back', 
            'image_left', 
            'image_right'
        )


class ScanDetailSerializer(serializers.ModelSerializer):
    scan_id = serializers.UUIDField(source='id', read_only=True)
    Name = serializers.SerializerMethodField()
    Date_of_Scan = serializers.DateTimeField(source='created_at', format="%B %d, %Y", read_only=True)
    status = serializers.CharField()
    thumbnail_image = serializers.ImageField(source='image_front', use_url=True, read_only=True)
    image_front_url = serializers.ImageField(source='image_front', use_url=True, read_only=True)
    image_back_url = serializers.ImageField(source='image_back', use_url=True, read_only=True)
    image_left_url = serializers.ImageField(source='image_left', use_url=True, read_only=True)
    image_right_url = serializers.ImageField(source='image_right', use_url=True, read_only=True)
    reconstructed_3d_head = serializers.FileField(source='processed_3d_model', use_url=True, read_only=True)
    Head_Width = serializers.CharField(source='head_width')
    Head_Length = serializers.CharField(source='head_length')
    Ear_to_Ear = serializers.CharField(source='ear_to_ear')
    Eye_to_Eye = serializers.CharField(source='eye_to_eye')
    Notes = serializers.CharField(source='notes')
    Custom_Fit = serializers.CharField(source='custom_field')

    class Meta:
        model = Scan
        fields = (
            'scan_id',
            'Name',
            'Date_of_Scan',
            'status',
            'thumbnail_image',
            'reconstructed_3d_head',
            'Head_Width',
            'Head_Length',
            'Ear_to_Ear',
            'Eye_to_Eye',
            'image_front_url',
            'image_back_url',
            'image_left_url',
            'image_right_url',
            'Notes',
            'Custom_Fit',
        )
        
    def get_Name(self, obj):
        if obj.user and obj.user.get_full_name():
            return obj.user.get_full_name()
        return "N/A"