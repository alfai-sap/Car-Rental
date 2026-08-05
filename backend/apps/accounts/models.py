from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email


class IdentityDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='identity_documents')
    document_type = models.CharField(max_length=50)  # e.g. 'drivers_license', 'passport', 'national_id'
    document_number = models.CharField(max_length=50)
    front_image = models.ImageField(upload_to='identity_docs/front/')
    back_image = models.ImageField(upload_to='identity_docs/back/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.email} - {self.document_type} ({self.document_number})"

