from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email


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

