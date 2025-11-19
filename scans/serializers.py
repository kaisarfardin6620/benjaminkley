from rest_framework import serializers
from .models import Scan, ScanImage
from django.conf import settings
from django.urls import reverse
from core.utils import get_full_media_url
from urllib.parse import urljoin

class ScanCreateSerializer(serializers.ModelSerializer):
    image_front = serializers.ImageField(required=True)
    
    extra_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=True
    )

    class Meta:
        model = Scan
        fields = ('name', 'notes', 'custom_field', 'image_front', 'extra_images')

    def validate(self, attrs):
        front = attrs.get('image_front')
        extras = attrs.get('extra_images', [])
        
        total_images = 1 + len(extras)
        
        if total_images < 5:
            raise serializers.ValidationError(f"You uploaded {total_images} images. Minimum 5 required.")
        return attrs

    def create(self, validated_data):
        extra_images_data = validated_data.pop('extra_images')
        
        scan = Scan.objects.create(**validated_data)
        
        scan_images = [ScanImage(scan=scan, image=img) for img in extra_images_data]
        ScanImage.objects.bulk_create(scan_images)
        
        return scan

class ScanDetailSerializer(serializers.ModelSerializer):
    scan_id = serializers.UUIDField(source='id', read_only=True)
    Name = serializers.CharField(source='name', default="N/A")
    Date_of_Scan = serializers.DateTimeField(source='created_at', format="%B %d, %Y", read_only=True)
    status = serializers.CharField()
    
    scan_images = serializers.SerializerMethodField()
    reconstructed_3d_head = serializers.SerializerMethodField()
    pdf_report_url = serializers.SerializerMethodField()
    
    Head_Width = serializers.CharField(source='head_width')
    Head_Length = serializers.CharField(source='head_length')
    Ear_to_Ear = serializers.CharField(source='ear_to_ear')
    Eye_to_Eye = serializers.CharField(source='eye_to_eye')
    Notes = serializers.CharField(source='notes')
    Custom_Fit = serializers.CharField(source='custom_field')

    class Meta:
        model = Scan
        fields = (
            'scan_id', 'Name', 'Date_of_Scan', 'status',
            'scan_images', 'reconstructed_3d_head', 'pdf_report_url',
            'Head_Width', 'Head_Length', 'Ear_to_Ear', 'Eye_to_Eye',
            'Notes', 'Custom_Fit'
        )

    def get_scan_images(self, obj):
        request = self.context.get('request')
        images = []
        front_url = get_full_media_url(request, obj.image_front)
        if front_url:
            images.append(front_url)
            
        for extra in obj.extra_images.all():
            url = get_full_media_url(request, extra.image)
            if url:
                images.append(url)
        
        return {"thumbnail": front_url, "all_images": images}

    def get_reconstructed_3d_head(self, obj):
        request = self.context.get('request')
        return get_full_media_url(request, obj.processed_3d_model)

    def get_pdf_report_url(self, obj):
        if obj.status == Scan.Status.COMPLETED:
            path = reverse('scan-view-pdf', kwargs={'pk': obj.pk})
            return urljoin(str(settings.SERVER_BASE_URL), path)
        return None