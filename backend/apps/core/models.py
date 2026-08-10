from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking_submitted', 'Booking Request Submitted'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('payment_required', 'Payment Required'),
        ('payment_successful', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('reschedule_requested', 'Reschedule Requested'),
        ('reschedule_approved', 'Reschedule Approved'),
        ('reschedule_rejected', 'Reschedule Rejected'),
        ('unit_assigned', 'Vehicle Unit Assigned'),
        ('unit_changed', 'Vehicle Unit Changed'),
        ('pickup_reminder', 'Pickup Reminder'),
        ('rental_activated', 'Rental Activated'),
        ('extension_requested', 'Extension Requested'),
        ('extension_approved', 'Extension Approved'),
        ('extension_rejected', 'Extension Rejected'),
        ('vehicle_returned', 'Vehicle Returned'),
        ('additional_payment_required', 'Additional Payment Required'),
        ('transaction_completed', 'Transaction Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=40, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    is_read = models.BooleanField(default=False)
    is_admin_notification = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_read', 'user']),
            models.Index(fields=['is_admin_notification', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} — {self.user.email}"


class AuditLog(models.Model):
    """Immutable audit trail for all admin actions on bookings and payments.

    Every admin-initiated state change is recorded with the acting user,
    target booking, action performed, and before/after snapshots.
    """
    ACTION_TYPES = [
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('payment_confirmed', 'Payment Manually Confirmed'),
        ('rental_activated', 'Rental Activated'),
        ('rental_completed', 'Rental Completed'),
        ('unit_assigned', 'Vehicle Unit Assigned'),
        ('unit_changed', 'Vehicle Unit Changed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_marked_waiting', 'Booking Marked Waiting'),
        ('profile_updated', 'Profile Updated'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=40, choices=ACTION_TYPES)
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    summary = models.CharField(max_length=500)
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['booking', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_action_display()}] by {self.actor.email} — {self.created_at}"

