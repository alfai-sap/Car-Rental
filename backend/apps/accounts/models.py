from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.validators import validate_image_size, validate_image_content


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{6,14}$',
                message='Enter a valid phone number (e.g. +639123456789).',
            ),
        ],
    )
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    # ── Account-level brute-force lockout ──
    # Tracks consecutive failed login attempts and enforces a
    # time-based lockout to prevent credential-stuffing attacks
    # that bypass IP-based throttling via distributed botnets.
    failed_login_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text='Consecutive failed login attempts. Reset on successful login.',
    )
    locked_until = models.DateTimeField(
        null=True, blank=True,
        help_text='Account is locked until this time. Null when not locked.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    # ── Lockout constants (overridable per deployment) ──
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)

    def __str__(self):
        return self.email

    def is_locked_out(self):
        """Return True if the account is currently locked due to failed attempts."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        # Lock has expired — clear it so the next good attempt works
        if self.locked_until and timezone.now() >= self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=['failed_login_attempts', 'locked_until'])
        return False

    def record_failed_login(self):
        """Increment failed attempts and lock account if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
            self.locked_until = timezone.now() + self.LOCKOUT_DURATION
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def clear_failed_attempts(self):
        """Reset the counter after a successful login."""
        if self.failed_login_attempts or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(update_fields=['failed_login_attempts', 'locked_until'])


class IdentityDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='identity_documents')
    document_type = models.CharField(max_length=50)  # e.g. 'drivers_license', 'passport', 'national_id'
    document_number = models.CharField(max_length=50)
    front_image = models.ImageField(
        upload_to='identity_docs/front/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size, validate_image_content],
    )
    back_image = models.ImageField(
        upload_to='identity_docs/back/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size, validate_image_content],
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.email} - {self.document_type} ({self.document_number})"

