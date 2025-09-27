from rest_framework import serializers
from .models import Scan
from django.conf import settings

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
    
    scan_images = serializers.SerializerMethodField()
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
            'scan_images',
            'reconstructed_3d_head',
            'Head_Width',
            'Head_Length',
            'Ear_to_Ear',
            'Eye_to_Eye',
            'Notes',
            'Custom_Fit',
        )
        
    def get_Name(self, obj):
        return obj.name if obj.name else "N/A"

    def get_scan_images(self, obj):
        request = self.context.get('request')
        if not request:
            return {"thumbnail": None, "all_images": []}

        images = []
        thumbnail = None

        if obj.image_front and hasattr(obj.image_front, 'url'):
            url = request.build_absolute_uri(obj.image_front.url)
            images.append(url)
            thumbnail = url
        if obj.image_back and hasattr(obj.image_back, 'url'):
            images.append(request.build_absolute_uri(obj.image_back.url))
        if obj.image_left and hasattr(obj.image_left, 'url'):
            images.append(request.build_absolute_uri(obj.image_left.url))
        if obj.image_right and hasattr(obj.image_right, 'url'):
            images.append(request.build_absolute_uri(obj.image_right.url))
        
        return {
            "thumbnail": thumbnail,
            "all_images": images
        }

    def get_reconstructed_3d_head(self, obj):
        request = self.context.get('request')
        if obj.processed_3d_model and hasattr(obj.processed_3d_model, 'url') and request:
            return request.build_absolute_uri(obj.processed_3d_model.url)
        return None