from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import calendar
from .serializers import *
from authentication.models import UserProfile, PasswordHistory
from scans.models import Scan
from contact_support.models import ContactMessage
from .models import *

class DashboardStatsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def _calculate_percentage_change(self, current_count, previous_count):
        """Helper function to calculate percentage change, avoiding division by zero."""
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

class AdminProfileView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        serializer = AdminProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        profile = request.user.profile
        
        serializer = AdminUpdateProfileSerializer(
            instance=profile, 
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(AdminProfileSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

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