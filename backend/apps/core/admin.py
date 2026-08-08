from django.contrib import admin
from apps.core.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'is_admin_notification', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_admin_notification', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
