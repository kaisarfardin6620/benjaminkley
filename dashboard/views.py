# dashboard/views.py

from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import get_object_or_404  
from datetime import timedelta
import calendar
from .serializers import *
from authentication.models import UserProfile, PasswordHistory
from scans.models import Scan
from contact_support.models import ContactMessage
from .models import *
from scans.tasks import process_scan_and_save
from notifications.utils import create_and_send_notification
from .models import AdminNotification, SiteContent
from fcm_django.models import FCMDevice
from firebase_admin import messaging
from django_filters.rest_framework import DjangoFilterBackend
from scans.filters import ScanDateFilter
from scans.pagination import ScanListPagination


class DashboardStatsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def _calculate_percentage_change(self, current_count, previous_count):
        if previous_count == 0:
            return 100.0 if current_count > 0 else 0.0
        return round(((current_count - previous_count) / previous_count) * 100, 2)

    def get(self, request):
        today = timezone.now().date()
        start_of_current_month = today.replace(day=1)
        start_of_previous_month = (start_of_current_month - timedelta(days=1)).replace(day=1)
        total_users = User.objects.count()
        total_scans = Scan.objects.count()
        users_this_month = User.objects.filter(date_joined__gte=start_of_current_month).count()
        scans_this_month = Scan.objects.filter(created_at__gte=start_of_current_month).count()
        users_last_month = User.objects.filter(
            date_joined__gte=start_of_previous_month,
            date_joined__lt=start_of_current_month
        ).count()
        scans_last_month = Scan.objects.filter(
            created_at__gte=start_of_previous_month,
            created_at__lt=start_of_current_month
        ).count()
        user_change = self._calculate_percentage_change(users_this_month, users_last_month)
        scan_change = self._calculate_percentage_change(scans_this_month, scans_last_month)
        return Response({
            "total_registered_user": {"count": total_users, "change": user_change},
            "total_3d_head_scanner": {"count": total_scans, "change": scan_change},
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
    queryset = User.objects.select_related('profile').prefetch_related('scans').order_by('-date_joined')
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email']

    @action(detail=True, methods=['post'], url_path='block')
    def block_user(self, request, pk=None):
        profile = get_object_or_404(UserProfile, user_id=pk)
        profile.status = 'Suspended'
        profile.save()
        create_and_send_notification(user=profile.user, title="Account Suspended", message="Your account has been suspended. Please contact support for more information.")
        return Response({'status': 'User blocked successfully.'})

    @action(detail=True, methods=['post'], url_path='unblock')
    def unblock_user(self, request, pk=None):
        profile = get_object_or_404(UserProfile, user_id=pk)
        profile.status = 'Active'
        profile.save()
        create_and_send_notification(user=profile.user, title="Account Re-activated", message="Your account has been re-activated and you can now use the app.")
        return Response({'status': 'User unblocked successfully.'})

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_user(self, request, pk=None):
        profile = get_object_or_404(UserProfile, user_id=pk)
        profile.status = 'Active'
        profile.save()
        create_and_send_notification(user=profile.user, title="Account Approved", message="Your account has been approved. You can now start using the app.")
        return Response({'status': 'User approved successfully.'})

class ScanManagementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DashboardScanSerializer
    queryset = Scan.objects.select_related('user').order_by('-created_at')
    pagination_class = ScanListPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ScanDateFilter
    search_fields = ['name', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'status']

    @action(detail=True, methods=['post'], url_path='rescan')
    def request_rescan(self, request, pk=None):
        scan = self.get_object()
        scan.status = Scan.Status.PROCESSING
        scan.save()
        process_scan_and_save.delay(str(scan.id))
        create_and_send_notification(
            user=scan.user,
            title="Re-Scan Requested",
            message=f"An admin has requested a re-scan of your scan named '{scan.name}'."
        )
        return Response({'status': f'Re-scan for scan ID {scan.id} has been queued.'})

class ContactMessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = DashboardContactMessageSerializer
    queryset = ContactMessage.objects.all().order_by('-created_at')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'message']
    ordering_fields = ['created_at', 'is_replied']


class PushNotificationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminNotificationSerializer
    queryset = AdminNotification.objects.filter(
        notification_type=AdminNotification.NotificationType.PUSH_SENT
    ).order_by('-created_at')
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'message']

class SendPushNotificationAPIView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, *args, **kwargs):
        serializer = PushNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        title = serializer.validated_data['title']
        message = serializer.validated_data['message']
        all_devices = FCMDevice.objects.filter(active=True)
        if all_devices:
            all_devices.send_message(
                messaging.Message(notification=messaging.Notification(title=title, body=message))
            )
        AdminNotification.objects.create(
            notification_type=AdminNotification.NotificationType.PUSH_SENT,
            title=title,
            message=message,
            is_read=True
        )
        return Response({"status": f"Push notification has been sent to {all_devices.count()} devices."}, status=status.HTTP_200_OK)
    
class AdminNotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminNotificationSerializer
    queryset = AdminNotification.objects.all().order_by('-created_at')
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read', 'notification_type']

    @action(detail=False, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request):
        ids_to_mark = request.data.get('ids', [])
        if not isinstance(ids_to_mark, list):
            return Response({"error": "Payload must be a list of IDs, e.g., {\"ids\": [1, 5, 10]}"}, status=status.HTTP_400_BAD_REQUEST)
        self.get_queryset().filter(id__in=ids_to_mark).update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

class SiteContentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = SiteContentSerializer
    queryset = SiteContent.objects.all().order_by('-updated_at')
    lookup_field = 'slug'

class AdminProfileView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        serializer = AdminProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        profile = user.profile
        full_name = request.data.get('full_name')
        if full_name:
            parts = full_name.strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        email = request.data.get('email')
        if email:
            user.email = email
            user.username = email
        user.save()
        profile_serializer = AdminUpdateProfileSerializer(instance=profile, data=request.data, partial=True)
        if profile_serializer.is_valid():
            profile_serializer.save()
            final_serializer = AdminProfileSerializer(user, context={'request': request})
            return Response(final_serializer.data)
        return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminChangePasswordView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, *args, **kwargs):
        serializer = AdminChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            PasswordHistory.objects.create(user=user, hashed_password=user.password)
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PrivacyPolicyAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        content = get_object_or_404(SiteContent, slug='privacy-policy')
        serializer = SiteContentSerializer(content)
        return Response(serializer.data)

class TermsAndConditionsAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        content = get_object_or_404(SiteContent, slug='terms-and-conditions')
        serializer = SiteContentSerializer(content)
        return Response(serializer.data)