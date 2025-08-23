from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import AuthToken, UserProfile, PasswordHistory
from .serializers import (
    SignupSerializer, OTPVerificationSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    ChangePasswordSerializer, ProfileSerializer, UpdateProfileSerializer,
    ProfilePictureSerializer, ResendVerificationSerializer,
    MyTokenObtainPairSerializer, LogoutSerializer
)
import random

def generate_otp():
    return str(random.randint(1000, 9999))

def send_email(subject, message, recipient_list):
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_otp_email(user, otp):
    subject = 'Your OTP for account verification'
    message = f'Hi {user.username}, your One-Time Password (OTP) is: {otp}. It is valid for 15 minutes.'
    return send_email(subject, message, [user.email])

class UserSignupAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp = generate_otp()
            AuthToken.objects.create(user=user, otp_code=otp, token_type='signup')
            send_otp_email(user, otp)
            return Response({"message": "User registered successfully. An OTP has been sent to your email."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifySignupOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            try:
                token = AuthToken.objects.get(otp_code=otp, token_type='signup', is_used=False)
            except AuthToken.DoesNotExist:
                return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
            if token.expires_at < timezone.now():
                return Response({'error': 'OTP has expired.'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = token.user
            user.is_active = True
            user.save()
            token.is_used = True
            token.save()
            return Response({'message': 'OTP verified successfully. Your account is now active.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendSignupOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            try:
                user = User.objects.get(username=username)
                if user.is_active:
                    return Response({'error': 'Account is already active.'}, status=status.HTTP_400_BAD_REQUEST)
                AuthToken.objects.filter(user=user, token_type='signup', is_used=False).update(is_used=True)
                otp = generate_otp()
                AuthToken.objects.create(user=user, otp_code=otp, token_type='signup')
                send_otp_email(user, otp)
                return Response({'message': 'New OTP sent to your email.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                return Response({'error': 'Account not active. Please verify your account first.'}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            # Let the parent class handle the "Invalid credentials" error
            pass
        return super().post(request, *args, **kwargs)
        
class UserLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token or token already blacklisted.'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        serializer = UpdateProfileSerializer(request.user.profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfilePictureUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = ProfilePictureSerializer(request.user.profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile picture updated successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            PasswordHistory.objects.create(user=user, hashed_password=user.password)
            return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(email=serializer.validated_data['email'])
                AuthToken.objects.filter(user=user, token_type='password_reset', is_used=False).update(is_used=True)
                token = AuthToken.objects.create(user=user, token_type='password_reset')
                subject = 'Password Reset Request'
                reset_link = f"http://YOUR-FRONTEND-URL/update-password/?token={token.token}"
                message = f'Hi {user.username},\n\nPlease click the link to reset your password: {reset_link}\n\nThis link is valid for 24 hours.'
                send_email(subject, message, [user.email])
                return Response({'message': 'Password reset link sent to your email.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User with this email not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        try:
            token = AuthToken.objects.get(
                token=data['token'], 
                token_type='password_reset', 
                is_used=False, 
                expires_at__gt=timezone.now()
            )
        except AuthToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        user = token.user
        new_password = data['new_password']

        # Optimized: Fetch only the 10 most recent hashed passwords
        recent_passwords = PasswordHistory.objects.filter(user=user).order_by('-created_at')[:10].values_list('hashed_password', flat=True)
        for hashed_password in recent_passwords:
            if check_password(new_password, hashed_password):
                return Response({'error': 'Cannot reuse recent passwords.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        
        # Save the new password to the history
        PasswordHistory.objects.create(user=user, hashed_password=user.password)
        
        token.is_used = True
        token.save()
        
        return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)

