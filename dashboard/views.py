# dashboard/views.py
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
from django.db.models import Count
import calendar

from .serializers import *
from authentication.models import UserProfile
from scans.models import Scan
from contact_support.models import ContactMessage
from .models import *

class DashboardStatsAPIView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        total_users = User.objects.count()
        total_scans = Scan.objects.count()
        return Response({
            "total_registered_user": {"count": total_users, "change": 12.0},
            "total_3d_head_scanner": {"count": total_scans, "change": 12.0},
        })

class UserOverviewChartAPIView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        data = User.objects.annotate(month=TruncMonth('date_joined')).values('month').annotate(count=Count('id')).order_by('month')
        monthly_counts = {item['month'].month: item['count'] for item in data if item['month']}
        final_data = [monthly_counts.get(i, 0) for i in range(1, 13)]
        return Response({"labels": [calendar.month_abbr[i] for i in range(1, 13)], "data": final_data})

class ScannerOverviewChartAPIView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        data = Scan.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(count=Count('id')).order_by('month')
        monthly_counts = {item['month'].month: item['count'] for item in data if item['month']}
        final_data = [monthly_counts.get(i, 0) for i in range(1, 13)]
        return Response({"labels": [calendar.month_abbr[i] for i in range(1, 13)], "data": final_data})

class UserManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DashboardUserSerializer
    queryset = User.objects.select_related('profile').prefetch_related('scans').all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email']

    @action(detail=True, methods=['post'], url_path='block')
    def block_user(self, request, pk=None):
        profile = UserProfile.objects.get(user_id=pk)
        profile.status = 'Suspended'
        profile.save()
        return Response({'status': 'User blocked'})
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_user(self, request, pk=None):
        profile = UserProfile.objects.get(user_id=pk)
        profile.status = 'Active'
        profile.save()
        return Response({'status': 'User approved'})

class ScanManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DashboardScanSerializer
    queryset = Scan.objects.select_related('user').all()

class ContactMessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DashboardContactMessageSerializer
    queryset = ContactMessage.objects.all().order_by('-created_at')

class PushNotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = PushNotificationSerializer
    queryset = PushNotification.objects.all().order_by('-sent_at')

    def perform_create(self, serializer):
        print(f"--- SIMULATING PUSH NOTIFICATION ---")
        print(f"Title: {serializer.validated_data['title']}")
        print(f"Message: {serializer.validated_data['message']}")
        serializer.save()

class AdminNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminNotificationSerializer
    queryset = AdminNotification.objects.all()

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

class SiteContentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = SiteContentSerializer
    queryset = SiteContent.objects.all()
    lookup_field = 'slug'