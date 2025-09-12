from rest_framework import serializers
from django.contrib.auth.models import User
from authentication.models import UserProfile
from scans.models import Scan
from contact_support.models import ContactMessage
from .models import PushNotification, AdminNotification, SiteContent
from authentication.serializers import PasswordValidator


class DashboardUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='profile.role', read_only=True)
    status = serializers.CharField(source='profile.status')
    date_of_birth = serializers.DateField(source='profile.date_of_birth', read_only=True)
    number_of_scan = serializers.SerializerMethodField()
    
    profile_picture = serializers.ImageField(source='profile.profile_picture', read_only=True, use_url=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name', 'email', 'profile_picture', # <-- Field added here
            'role', 'date_of_birth', 'number_of_scan', 'status', 'date_joined'
        )
    
    def get_number_of_scan(self, obj):
        return obj.scans.count()

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        status = profile_data.get('status')
        profile = instance.profile
        if status is not None:
            profile.status = status
            profile.save()
        return super().update(instance, validated_data)


class DashboardScanSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    submission_date = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = Scan
        fields = ('id', 'name', 'email', 'submission_date', 'status', 'processed_3d_model')

class DashboardContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'

class PushNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = '__all__'
        read_only_fields = ('sent_at',)

class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = '__all__'

class SiteContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteContent
        fields = '__all__'
        read_only_fields = ('slug',)

class AdminProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')
    email = serializers.EmailField()
    contact_number = serializers.CharField(source='profile.contact_number')
    
    profile_picture = serializers.ImageField(source='profile.profile_picture', use_url=True, read_only=True)

    class Meta:
        model = User
        fields = ('full_name', 'email', 'contact_number', 'profile_picture')


class AdminUpdateProfileSerializer(serializers.ModelSerializer):
    
    profile_picture = serializers.ImageField(required=False, write_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('contact_number', 'profile_picture')
    
class AdminChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[PasswordValidator.validate_password_strength])
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is not correct.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data