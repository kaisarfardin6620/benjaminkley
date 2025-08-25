from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    role = models.CharField(max_length=255)
    clinic_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    contact_number = models.CharField(max_length=20, validators=[RegexValidator(regex=r"^\+?[1-9]\d{1,14}$", message="Phone number must be in E.164 format: '+1234567890'")])
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return f"<User object: {self.user.first_name} {self.user.last_name}>"

class AuthToken(models.Model):
    TOKEN_TYPES = (
        ('signup', 'Signup Verification'),
        ('password_reset_otp', 'Password Reset OTP'),
        ('password_change_ticket', 'Password Change Ticket'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_tokens')
    token_type = models.CharField(max_length=30, choices=TOKEN_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

class PasswordHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    hashed_password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        histories = PasswordHistory.objects.filter(user=self.user).order_by('-created_at')
        if histories.count() > 10:
            histories.last().delete()