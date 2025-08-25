from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import (
    MyTokenObtainPairView,
    UserSignupAPIView,
    VerifySignupOTPView,
    UserLogoutAPIView, 
    UserProfileAPIView,
    UpdateProfileAPIView,
    ChangePasswordAPIView, 
    PasswordResetRequestOTPView,
    VerifyPasswordResetOTPView,
    SetNewPasswordView, 
    ProfilePictureUploadAPIView,
    ResendSignupOTPView,
    DeleteUserAccountAPIView,

    
)

urlpatterns = [
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('logout/', UserLogoutAPIView.as_view(), name='logout'),

    path('signup/', UserSignupAPIView.as_view(), name='signup'),
    path('signup/verify/', VerifySignupOTPView.as_view(), name='verify-signup-otp'),
    path('signup/resend-otp/', ResendSignupOTPView.as_view(), name='resend-signup-otp'),

    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('profile/update/', UpdateProfileAPIView.as_view(), name='update-profile'),
    path('profile/picture/upload/', ProfilePictureUploadAPIView.as_view(), name='profile-picture-upload'),

    path('password/change/', ChangePasswordAPIView.as_view(), name='password-change'),
    
    path('password/reset/request-otp/', PasswordResetRequestOTPView.as_view(), name='password-reset-request-otp'),
    path('password/reset/verify-otp/', VerifyPasswordResetOTPView.as_view(), name='password-reset-verify-otp'),
    path('password/reset/set-new/', SetNewPasswordView.as_view(), name='password-reset-set-new'),

    path('profile/delete/', DeleteUserAccountAPIView.as_view(), name='delete-user-account'),
]