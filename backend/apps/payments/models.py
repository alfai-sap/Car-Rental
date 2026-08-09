import uuid

from django.db import models


class Invoice(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_OVERDUE = 'overdue'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=12, unique=True, editable=False)
    booking = models.OneToOneField('bookings.Booking', on_delete=models.PROTECT, related_name='invoice')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} ({self.booking.booking_number})'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f'INV-{uuid.uuid4().hex[:8].upper()}'
        self.total = (self.subtotal or 0) + (self.additional_charges or 0) - (self.discount or 0)
        if self.total < 0:
            self.total = 0
        super().save(*args, **kwargs)


class Payment(models.Model):
    PROVIDER_DISABLED = 'disabled'
    PROVIDER_PAYMONGO = 'paymongo'

    PROVIDER_CHOICES = [
        (PROVIDER_DISABLED, 'Disabled'),
        (PROVIDER_PAYMONGO, 'PayMongo'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    payment_number = models.CharField(max_length=12, unique=True, editable=False)
    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_DISABLED)
    provider_reference = models.CharField(max_length=120, blank=True)
    checkout_url = models.URLField(blank=True)
    currency = models.CharField(max_length=3, default='PHP')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    webhook_event_id = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='PayMongo event ID for idempotency — prevents double-processing of webhooks.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.payment_number} ({self.payment_status})'

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = f'PMT-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def mark_paid(self, paid_at=None):
        from django.utils import timezone

        self.payment_status = self.STATUS_PAID
        self.paid_at = paid_at or timezone.now()
        self.save(update_fields=['payment_status', 'paid_at', 'updated_at'])

