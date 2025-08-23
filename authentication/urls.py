from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    MyTokenObtainPairView, UserSignupAPIView, VerifySignupOTPView, UserLogoutAPIView, 
    UserProfileAPIView, UpdateProfileAPIView, ChangePasswordAPIView, 
    PasswordResetRequestAPIView, PasswordResetConfirmAPIView, ProfilePictureUploadAPIView,
    ResendSignupOTPView,
)

urlpatterns = [
    # Token Management
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('logout/', UserLogoutAPIView.as_view(), name='logout'),

    # Signup Flow
    path('signup/', UserSignupAPIView.as_view(), name='signup'),
    path('signup/verify/', VerifySignupOTPView.as_view(), name='verify-signup-otp'),
    path('signup/resend-otp/', ResendSignupOTPView.as_view(), name='resend-signup-otp'),

    # Profile Management
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('profile/update/', UpdateProfileAPIView.as_view(), name='update-profile'),
    path('profile/picture/upload/', ProfilePictureUploadAPIView.as_view(), name='profile-picture-upload'),

    # Password Management
    path('password/change/', ChangePasswordAPIView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestAPIView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmAPIView.as_view(), name='password-reset-confirm'),

]