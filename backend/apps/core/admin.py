from django.contrib import admin
from apps.core.models import Notification, AuditLog, RentalDiscountPolicy, DiscountTier


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'is_admin_notification', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_admin_notification', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


class DiscountTierInline(admin.TabularInline):
    model = DiscountTier
    extra = 1
    min_num = 1


@admin.register(RentalDiscountPolicy)
class RentalDiscountPolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'created_at', 'updated_at']
    list_filter = ['is_default']
    search_fields = ['name']
    inlines = [DiscountTierInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['actor', 'action', 'summary', 'booking', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['actor__email', 'summary', 'booking__booking_number']
    readonly_fields = ['actor', 'action', 'booking', 'payment', 'summary', 'before_state', 'after_state', 'ip_address', 'created_at']
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # audit logs are append-only, never manually created

    def has_change_permission(self, request, obj=None):
        return False  # immutable

    def has_delete_permission(self, request, obj=None):
        return False  # immutable
