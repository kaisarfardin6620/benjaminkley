from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]