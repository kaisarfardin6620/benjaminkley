# dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='dashboard-user')
router.register(r'scans', ScanManagementViewSet, basename='dashboard-scan')
router.register(r'contacts', ContactMessageViewSet, basename='dashboard-contact')
router.register(r'push-notifications', PushNotificationViewSet, basename='push-notification')
router.register(r'admin-notifications', AdminNotificationViewSet, basename='admin-notification')
router.register(r'content', SiteContentViewSet, basename='site-content')

urlpatterns = [
    path('stats/', DashboardStatsAPIView.as_view(), name='dashboard-stats'),
    path('charts/user-overview/', UserOverviewChartAPIView.as_view(), name='chart-user-overview'),
    path('charts/scanner-overview/', ScannerOverviewChartAPIView.as_view(), name='chart-scanner-overview'),
    path('', include(router.urls)),
]