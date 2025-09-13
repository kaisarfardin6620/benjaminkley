import re
import hashlib
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework import serializers
from .models import UserProfile, PasswordHistory, Roles
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.urls import reverse

class RoleChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        for key, value in self._choices.items():
            if value == data:
                return key
        self.fail('invalid_choice', input=data)
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
    role = RoleChoiceField(choices=Roles.choices)
    clinic_name = serializers.CharField(max_length=255, required=True)
    date_of_birth = serializers.DateField(required=True, input_formats=['%m-%d-%Y'])
    contact_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(max_length=255, required=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if User.objects.filter(email__iexact=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use by another account."})
        data.pop('confirm_password', None)
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            is_active=True
        )

        profile = user.profile
        
        profile.role = validated_data.get('role', profile.role)
        profile.clinic_name = validated_data.get('clinic_name', profile.clinic_name)
        profile.date_of_birth = validated_data.get('date_of_birth', profile.date_of_birth)
        profile.contact_number = validated_data.get('contact_number', profile.contact_number)
        profile.address = validated_data.get('address', profile.address)
        profile.profile_picture = validated_data.get('profile_picture', profile.profile_picture)
        
        profile.status = 'Active'
        
        profile.save()

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
    profile_picture = serializers.ImageField(use_url=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'email', 'profile_picture', 'role',
            'clinic_name', 'date_of_birth', 'contact_number', 'address', 'status'
        ]
class UpdateProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, write_only=True)
    role = RoleChoiceField(choices=Roles.choices, required=False)
    clinic_name = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False)
    address = serializers.CharField(required=False)

    def update(self, instance, validated_data):
        profile = instance.profile

        if 'full_name' in validated_data:
            full_name = validated_data['full_name'].strip()
            parts = full_name.split(' ', 1)
            instance.first_name = parts[0]
            instance.last_name = parts[1] if len(parts) > 1 else ''
        if 'role' in validated_data:
            profile.role = validated_data['role']
        if 'clinic_name' in validated_data:
            profile.clinic_name = validated_data['clinic_name']
        if 'date_of_birth' in validated_data:
            profile.date_of_birth = validated_data['date_of_birth']
        if 'address' in validated_data:
            profile.address = validated_data['address']

        instance.save()  
        profile.save()   
        
        return instance

class ProfilePictureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']
    def update(self, instance, validated_data):
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.save()
        return instance

class ResendVerificationSerializer(serializers.Serializer):
    username = serializers.CharField()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise serializers.ValidationError('No active account found with the given credentials.')

        if not user.check_password(password):
            raise serializers.ValidationError('No active account found with the given credentials.')
        
        if not user.is_active:
             raise serializers.ValidationError('This account is not active. Please verify your email first.')

        data = super().validate(attrs)

        structured_response = {
            'custom_meta': {
                "message": "Successfully Logged in."
            },
            "user": {
                "id": user.pk,
                "email": user.email,
                "role": "ADMIN" if user.is_staff else user.profile.role
            },
            "token": data['access'],
            "refresh_token": data['refresh']
        }
        
        return structured_response

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