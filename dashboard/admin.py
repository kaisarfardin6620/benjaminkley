# dashboard/admin.py
from django.contrib import admin
from .models import PushNotification, AdminNotification, SiteContent

@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'sent_to', 'sent_at')
    readonly_fields = ('title', 'message', 'sent_to', 'sent_at')
    def has_add_permission(self, request): return False

@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_read', 'created_at')

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}