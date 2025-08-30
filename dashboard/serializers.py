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
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'role', 'date_of_birth', 'number_of_scan', 'status', 'date_joined')
    
    def get_number_of_scan(self, obj):
        return obj.scans.count()

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
    profile_picture = serializers.ImageField(source='profile.profile_picture', use_url=True)

    class Meta:
        model = User
        fields = ('full_name', 'email', 'contact_number', 'profile_picture')


class AdminUpdateProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    
    class Meta:
        model = UserProfile
        fields = ('full_name', 'email', 'contact_number', 'profile_picture')

    def update(self, instance, validated_data):
        user = instance.user

        user_data = validated_data.pop('user', {})
        if 'get_full_name' in user_data:
            full_name = user_data['get_full_name'].strip()
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        
        if 'email' in user_data:
            user.email = user_data['email']
            user.username = user_data['email'] 
        
        user.save()

        return super().update(instance, validated_data)
    
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