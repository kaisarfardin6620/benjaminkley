from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import PrivacyPolicyAPIView, TermsAndConditionsAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/contact/', include('contact_support.urls')),
    path('api/scans/', include('scans.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/privacy-policy/', PrivacyPolicyAPIView.as_view(), name='privacy-policy'),
    path('api/terms-and-conditions/', TermsAndConditionsAPIView.as_view(), name='terms-and-conditions'),
    path('api/notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)