import re
import hashlib
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from .models import UserProfile, PasswordHistory
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class PasswordValidator:
    @staticmethod
    def validate_breached_password(password):
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        try:
            response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}", timeout=3)
            return suffix in response.text
        except requests.RequestException:
            return False

    @staticmethod
    def validate_password_strength(password):
        if len(password) < 10:
            raise serializers.ValidationError("Password must be at least 10 characters long.")
        if not re.search(r"[A-Z]", password):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", password):
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise serializers.ValidationError("Password must contain at least one special character.")

class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[PasswordValidator.validate_password_strength])
    confirm_password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=255, required=True)
    last_name = serializers.CharField(max_length=255, required=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    role = serializers.CharField(max_length=255, required=True)
    clinic_name = serializers.CharField(max_length=255, required=True)
    date_of_birth = serializers.DateField(required=True, input_formats=['%m-%d-%Y'])
    contact_number = serializers.CharField(max_length=20, required=True)
    address = serializers.CharField(max_length=255, required=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use by another account."})
        if PasswordValidator.validate_breached_password(data['password']):
            raise serializers.ValidationError({"password": "This password has been found in a data breach. Please choose a different one."})
        data.pop('confirm_password', None)
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            is_active=False
        )
        UserProfile.objects.create(
            user=user,
            profile_picture=validated_data.get('profile_picture'),
            role=validated_data.get('role'),
            clinic_name=validated_data.get('clinic_name'),
            date_of_birth=validated_data.get('date_of_birth'),
            contact_number=validated_data.get('contact_number'),
            address=validated_data.get('address')
        )
        return user

class OTPVerificationSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[PasswordValidator.validate_password_strength])
    new_password_confirmation = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        if PasswordValidator.validate_breached_password(value):
            raise serializers.ValidationError("This password has been found in a data breach. Please choose a different one.")
        if user.check_password(value):
            raise serializers.ValidationError("New password cannot be the same as the old password.")
        for history in PasswordHistory.objects.filter(user=user).order_by('-created_at')[:10]:
            if check_password(value, history.hashed_password):
                raise serializers.ValidationError("Cannot reuse a recent password.")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirmation']:
            raise serializers.ValidationError({"new_password_confirmation": "New passwords do not match."})
        return data

class ProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'role', 'clinic_name', 'date_of_birth', 'contact_number', 'address', 'status']

class UpdateProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    date_of_birth = serializers.DateField(required=False, input_formats=['%m-%d-%Y'])

    class Meta:
        model = UserProfile
        fields = ['first_name', 'role', 'clinic_name', 'date_of_birth', 'address']

    def update(self, instance, validated_data):
        user = instance.user
        
        user_data = validated_data.get('user', {})
        user.first_name = user_data.get('first_name', user.first_name)
        user.save()

        instance.role = validated_data.get('role', instance.role)
        instance.clinic_name = validated_data.get('clinic_name', instance.clinic_name)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.address = validated_data.get('address', instance.address)
        instance.save()
        
        return instance

class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']

class ResendVerificationSerializer(serializers.Serializer):
    username = serializers.CharField()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetVerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, min_length=6)

class SetNewPasswordSerializer(serializers.Serializer):
    password_change_ticket = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, required=True, validators=[PasswordValidator.validate_password_strength])
    new_password_confirmation = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirmation']:
            raise serializers.ValidationError({"new_password_confirmation": "Passwords do not match."})
        if PasswordValidator.validate_breached_password(data['new_password']):
            raise serializers.ValidationError({"new_password": "This password has been found in a data breach."})
        return data
    
class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your password was incorrect. Please try again.")
        return value