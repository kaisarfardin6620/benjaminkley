# dashboard/models.py
from django.db import models

class PushNotification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    sent_to = models.CharField(max_length=100, default="All Clients")
    sent_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-sent_at']
    def __str__(self):
        return self.title

class AdminNotification(models.Model):
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.message

class SiteContent(models.Model):
    slug = models.SlugField(unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title