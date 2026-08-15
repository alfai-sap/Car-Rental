from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.core.validators import validate_image_size, validate_image_content
from apps.core.storage import private_identity_storage


class UserManager(BaseUserManager):
    """Manager for the custom email-based User model.

    Usernames are generated automatically from the email local-part when
    not explicitly provided, so callers (and `createsuperuser`) only need
    to supply an email address.
    """
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email address must be set.')
        email = self.normalize_email(email).lower()

        username = extra_fields.pop('username', None)
        if username:
            # Explicit username — the caller is responsible for uniqueness.
            user = self.model(email=email, username=username, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            return user

        # Auto-generate a username from the email local-part.  Two concurrent
        # registrations sharing the same local-part (e.g. john@gmail.com and
        # john@yahoo.com) can both pass the existence check before either row
        # is committed, racing on the unique constraint.  Retry with an
        # incremented suffix on IntegrityError instead of surfacing a 500.
        base_username = email.split('@')[0]
        suffix = 0
        while True:
            candidate = base_username if suffix == 0 else f'{base_username}{suffix}'
            user = self.model(email=email, username=candidate, **extra_fields)
            user.set_password(password)
            try:
                # Savepoint isolation: a failed INSERT must not poison an
                # enclosing transaction, so the retry below always succeeds.
                with transaction.atomic(using=self._db):
                    user.save(using=self._db)
                return user
            except IntegrityError:
                # If the email itself is already registered, a new username
                # can never resolve the conflict — re-raise the real error.
                if self.filter(email=email).exists():
                    raise
                suffix += 1

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    # ── Authentication methods ──
    AUTH_METHOD_EMAIL = 'email'
    AUTH_METHOD_GOOGLE = 'google'
    AUTH_METHOD_CHOICES = [
        (AUTH_METHOD_EMAIL, 'Email'),
        (AUTH_METHOD_GOOGLE, 'Google'),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^09\d{9}$',
                message='Enter a valid 11-digit mobile number (e.g. 09123456789).',
            ),
        ],
    )
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    auth_method = models.CharField(
        max_length=10,
        choices=AUTH_METHOD_CHOICES,
        default=AUTH_METHOD_EMAIL,
        help_text='How this account authenticates (email/password or Google).',
    )

    # ── Session revocation ──
    # Bumped whenever every outstanding session for this account must be
    # invalidated immediately (password change/reset, email verification,
    # sign-out).  Access tokens carry this value as the `token_version`
    # claim; the custom JWT authentication rejects tokens whose version
    # no longer matches.  See apps/accounts/authentication.py.
    token_version = models.PositiveIntegerField(
        default=0,
        help_text='Increment to revoke all previously issued access tokens.',
    )

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

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # ── Lockout constants (overridable per deployment) ──
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)

    def __str__(self):
        return self.email

    # ── Booking eligibility helpers ──
    def is_profile_complete(self):
        """True when the customer has provided all required profile fields."""
        return bool(self.first_name and self.last_name and self.phone)

    def is_identity_complete(self):
        """True when the customer has at least one driver's license on file."""
        return self.identity_documents.filter(document_type='drivers_license').exists()

    def is_booking_eligible(self):
        """A customer may book only when email is verified, profile is
        complete, and identity documents are on file."""
        return (
            self.is_verified
            and self.is_profile_complete()
            and self.is_identity_complete()
        )

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

    def revoke_all_sessions(self):
        """Invalidate every outstanding session for this account.

        Bumps `token_version` so that all previously issued access tokens
        fail the version check in the custom JWT authentication, and
        blacklists every outstanding refresh token so none of them can mint
        a new access token.  The caller is responsible for persisting the
        version bump (this method only mutates the in-memory instance).

        Blacklisting (rather than deleting) the outstanding tokens is
        deliberate: deleting them would cascade-delete their blacklist
        entries and could un-revoke a token.
        """
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        self.token_version = (self.token_version or 0) + 1
        for outstanding in OutstandingToken.objects.filter(user=self):
            BlacklistedToken.objects.get_or_create(token=outstanding)


class IdentityDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='identity_documents')
    document_type = models.CharField(max_length=50)  # e.g. 'drivers_license', 'passport', 'national_id'
    document_number = models.CharField(max_length=50)
    front_image = models.ImageField(
        upload_to='identity_docs/front/',
        storage=private_identity_storage,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size, validate_image_content],
    )
    back_image = models.ImageField(
        upload_to='identity_docs/back/',
        storage=private_identity_storage,
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), validate_image_size, validate_image_content],
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.email} - {self.document_type} ({self.document_number})"

