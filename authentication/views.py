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
    SignupSerializer, OTPVerificationSerializer, ChangePasswordSerializer, 
    ProfileSerializer, UpdateProfileSerializer, ProfilePictureSerializer, 
    ResendVerificationSerializer, MyTokenObtainPairSerializer, LogoutSerializer,
    PasswordResetRequestSerializer, PasswordResetVerifyOTPSerializer, SetNewPasswordSerializer,DeleteAccountSerializer
)
import random

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email(subject, message, recipient_list):
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_otp_email(user, otp, purpose="account verification"):
    subject = f'Your OTP for {purpose}'
    message = f'Hi {user.username},\n\nYour One-Time Password (OTP) is: {otp}\n\nIt is valid for 15 minutes.'
    return send_email(subject, message, [user.email])

class UserSignupAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp = generate_otp()
            AuthToken.objects.create(user=user, otp_code=otp, token_type='signup')
            send_otp_email(user, otp, purpose="account verification")
            return Response({"message": "User registered successfully. An OTP has been sent to your email."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifySignupOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        try:
            token = AuthToken.objects.get(otp_code=otp, token_type='signup', is_used=False, expires_at__gt=timezone.now())
        except AuthToken.DoesNotExist:
            return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = token.user
        user.is_active = True
        user.save()
        token.is_used = True
        token.save()
        return Response({'message': 'OTP verified successfully. Your account is now active.'}, status=status.HTTP_200_OK)

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
                send_otp_email(user, otp, purpose="account verification")
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
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        profile = request.user.profile
        serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProfileSerializer(profile).data, status=status.HTTP_200_OK)
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
class PasswordResetRequestOTPView(APIView):
    """STEP 1: User provides email to request a password reset OTP."""
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                AuthToken.objects.filter(user=user, token_type='password_reset_otp').delete()
                otp = generate_otp()
                AuthToken.objects.create(user=user, otp_code=otp, token_type='password_reset_otp')
                send_otp_email(user, otp, purpose="password reset")
            except User.DoesNotExist:
                pass
            return Response({'message': 'If an account with this email exists, an OTP has been sent.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']

        try:
            token = AuthToken.objects.get(
                otp_code=otp, token_type='password_reset_otp', 
                is_used=False, expires_at__gt=timezone.now()
            )
        except AuthToken.DoesNotExist:
            return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        token.is_used = True
        token.save()

        change_ticket = AuthToken.objects.create(user=token.user, token_type='password_change_ticket')
        
        return Response({
            'message': 'OTP verified successfully.',
            'password_change_ticket': change_ticket.token
        }, status=status.HTTP_200_OK)

class SetNewPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
            
        ticket = serializer.validated_data['password_change_ticket']
        new_password = serializer.validated_data['new_password']

        try:
            verified_token = AuthToken.objects.get(
                token=ticket, token_type='password_change_ticket',
                is_used=False, expires_at__gt=timezone.now()
            )
        except AuthToken.DoesNotExist:
            return Response({'error': 'Invalid or expired password change session. Please start over.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = verified_token.user
        
        recent_passwords = PasswordHistory.objects.filter(user=user).order_by('-created_at')[:10].values_list('hashed_password', flat=True)
        for hashed_password in recent_passwords:
            if check_password(new_password, hashed_password):
                return Response({'error': 'Cannot reuse a recent password.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        PasswordHistory.objects.create(user=user, hashed_password=user.password)
        
        verified_token.is_used = True
        verified_token.save()
        
        return Response({'message': 'Your password has been reset successfully.'}, status=status.HTTP_200_OK)
    

class DeleteUserAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        serializer = DeleteAccountSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.delete()

        return Response(
            {"message": "Your account has been permanently deleted."},
            status=status.HTTP_200_OK
        )    