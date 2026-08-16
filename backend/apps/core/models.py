from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings


class Notification(models.Model):
    # ── Notification type catalogue ──
    #
    # ACTIVE: emitted by the notification service and consumed by the
    # frontend NotificationsView.
    #
    # RESERVED (unused): kept in the schema so historical rows with these
    # values remain valid, and for upcoming features.  They are NOT emitted
    # by any code path today:
    #   * reschedule_requested / reschedule_approved / reschedule_rejected
    #     — no reschedule feature is implemented.
    #   * extension_requested / extension_approved / extension_rejected
    #     — reserved for the upcoming extension feature.
    #   * additional_payment_required — reserved for the upcoming
    #     refund / extension feature.
    NOTIFICATION_TYPES = [
        ('booking_submitted', 'Booking Request Submitted'),
        ('booking_approved', 'Booking Approved'),
        ('booking_rejected', 'Booking Rejected'),
        ('payment_required', 'Payment Required'),
        ('payment_successful', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('booking_confirmed', 'Booking Confirmed'),
        # Reserved (unused) — reschedule flow not implemented.
        ('reschedule_requested', 'Reschedule Requested'),
        ('reschedule_approved', 'Reschedule Approved'),
        ('reschedule_rejected', 'Reschedule Rejected'),
        ('unit_assigned', 'Vehicle Unit Assigned'),
        ('unit_changed', 'Vehicle Unit Changed'),
        ('pickup_reminder', 'Pickup Reminder'),
        ('rental_activated', 'Rental Activated'),
        # Reserved (unused) — upcoming extension feature.
        ('extension_requested', 'Extension Requested'),
        ('extension_approved', 'Extension Approved'),
        ('extension_rejected', 'Extension Rejected'),
        ('vehicle_returned', 'Vehicle Returned'),
        # Reserved (unused) — upcoming refund / extension feature.
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


class RentalDiscountPolicy(models.Model):
    """A global, duration-based rental discount policy.

    Discounts are applied by the number of rental days (inclusive).  The
    policy is fleet-wide by default; an individual Vehicle may optionally
    reference a different policy later to override the global default while
    the MVP stays simple and centrally managed.

    A policy contains an ordered list of tiers; the longest matching day
    count wins.  Example:

        1–6 days   → 0%
        7–29 days  → 10%
        30+ days   → 20%
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text='The active global policy applied fleet-wide when a vehicle '
                  'has no explicit override.  Only one policy can be default.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rental discount policy'
        verbose_name_plural = 'Rental discount policies'

    def __str__(self):
        return f"{self.name}{' (default)' if self.is_default else ''}"

    def clean(self):
        super().clean()
        if self.is_default:
            conflict = (
                RentalDiscountPolicy.objects
                .filter(is_default=True)
                .exclude(pk=self.pk)
                .exists()
            )
            if conflict:
                raise ValidationError(
                    {'is_default': 'Another policy is already marked as default.'}
                )

    def save(self, *args, **kwargs):
        if self.is_default:
            # Enforce a single default policy: demote any existing default
            # before validating, so clean() sees a consistent state.
            RentalDiscountPolicy.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        """Return the active default policy, or None if none is configured."""
        return cls.objects.filter(is_default=True).first()

    def discount_percent_for_days(self, days):
        """Return the discount percentage (0–100) for the given rental days.

        Uses the longest matching minimum-days tier; a null min_days tier
        matches any count.  Ties are resolved in favour of the highest
        percentage.
        """
        if days is None or days < 1:
            days = 1
        matching = [
            tier for tier in self.tiers.all()
            if tier.min_days is None or days >= tier.min_days
        ]
        if not matching:
            return Decimal('0')
        # Longest applicable duration wins; on a tie, the higher discount.
        best = max(
            matching,
            key=lambda t: ((t.min_days or 0), t.discount_percent),
        )
        return Decimal(best.discount_percent)


class DiscountTier(models.Model):
    """A single discount tier within a RentalDiscountPolicy.

    `min_days` is the inclusive lower bound of the tier.  A tier with
    min_days=1 and percent=0 represents the no-discount base range.
    """
    policy = models.ForeignKey(
        RentalDiscountPolicy,
        on_delete=models.CASCADE,
        related_name='tiers',
    )
    min_days = models.PositiveIntegerField(default=1)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Discount percentage (0–100) for rentals of min_days or more.',
    )

    class Meta:
        ordering = ['min_days']
        constraints = [
            models.UniqueConstraint(
                fields=['policy', 'min_days'],
                name='%(app_label)s_%(class)s_unique_policy_min_days',
            ),
        ]

    def __str__(self):
        return f"{self.policy.name}: {self.min_days}+ days → {self.discount_percent}%"

    def clean(self):
        super().clean()
        if self.discount_percent is None:
            return
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError(
                {'discount_percent': 'Discount must be between 0 and 100.'}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

