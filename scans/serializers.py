from rest_framework import serializers
from .models import Scan
from django.conf import settings # <-- ADDED THIS IMPORT

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
    
    # --- THESE ARE THE FIXES ---
    thumbnail_image = serializers.SerializerMethodField()
    image_front_url = serializers.SerializerMethodField()
    image_back_url = serializers.SerializerMethodField()
    image_left_url = serializers.SerializerMethodField()
    image_right_url = serializers.SerializerMethodField()
    reconstructed_3d_head = serializers.SerializerMethodField()
    
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

    # --- ADDED THESE METHODS ---
    def get_thumbnail_image(self, obj):
        if obj.image_front:
            return f"{settings.SERVER_BASE_URL}{obj.image_front.url}"
        return None

    def get_image_front_url(self, obj):
        if obj.image_front:
            return f"{settings.SERVER_BASE_URL}{obj.image_front.url}"
        return None

    def get_image_back_url(self, obj):
        if obj.image_back:
            return f"{settings.SERVER_BASE_URL}{obj.image_back.url}"
        return None

    def get_image_left_url(self, obj):
        if obj.image_left:
            return f"{settings.SERVER_BASE_URL}{obj.image_left.url}"
        return None

    def get_image_right_url(self, obj):
        if obj.image_right:
            return f"{settings.SERVER_BASE_URL}{obj.image_right.url}"
        return None

    def get_reconstructed_3d_head(self, obj):
        if obj.processed_3d_model:
            return f"{settings.SERVER_BASE_URL}{obj.processed_3d_model.url}"
        return None