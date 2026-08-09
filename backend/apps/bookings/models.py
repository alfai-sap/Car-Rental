import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('confirmed', 'Confirmed'),
        ('waiting_for_pickup', 'Waiting for Pickup'),
        ('active', 'Active Rental'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    RETURN_UNIT_STATUS_CHOICES = [
        ('available', 'Available'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    ]

    booking_number = models.CharField(max_length=12, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    vehicle_unit = models.ForeignKey(
        'vehicles.VehicleUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    pickup_date = models.DateField()
    return_date = models.DateField()
    pickup_time = models.TimeField()
    return_time = models.TimeField(default='17:00')
    rental_days = models.PositiveSmallIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_approval')
    special_request = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    handover_time = models.DateTimeField(null=True, blank=True)
    return_time_actual = models.DateTimeField(null=True, blank=True)
    return_unit_status = models.CharField(
        max_length=20, choices=RETURN_UNIT_STATUS_CHOICES, blank=True,
        help_text='Post-return status of the vehicle unit (available/maintenance/inactive). '
                   'Must be recorded before completing the transaction.',
    )
    # Identity snapshot — immutable record of customer identity at booking time
    identity_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking_number} — {self.vehicle} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = self._generate_booking_number()
        if self.rental_days is None or not self.rental_days:
            if self.return_date <= self.pickup_date:
                raise ValueError('Return date must be after pickup date.')
            self.rental_days = max(1, (self.return_date - self.pickup_date).days + 1)
        if self.subtotal is None:
            self.subtotal = self.vehicle.price_per_day * self.rental_days
        if self.estimated_total is None:
            self.estimated_total = self.subtotal  # deposits/taxes added in Phase 5
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_booking_number():
        return f"BK-{uuid.uuid4().hex[:8].upper()}"


class AssignmentHistory(models.Model):
    """Immutable log of every vehicle unit assignment change for a booking."""
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='assignment_history',
    )
    previous_unit = models.ForeignKey(
        'vehicles.VehicleUnit', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='previous_assignments',
    )
    new_unit = models.ForeignKey(
        'vehicles.VehicleUnit', on_delete=models.PROTECT, related_name='new_assignments',
    )
    reason = models.CharField(max_length=255)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unit_assignments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Assignment histories'

    def __str__(self):
        prev = self.previous_unit.plate_number if self.previous_unit else 'None'
        new = self.new_unit.plate_number
        return f"Booking {self.booking.booking_number}: {prev} → {new} ({self.reason})"
