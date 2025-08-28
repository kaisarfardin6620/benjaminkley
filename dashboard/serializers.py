# dashboard/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from authentication.models import UserProfile
from scans.models import Scan
from contact_support.models import ContactMessage
from .models import PushNotification, AdminNotification, SiteContent

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