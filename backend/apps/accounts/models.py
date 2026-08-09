from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def _validate_image_size(image):
    """Reject images larger than 10 MB."""
    limit_mb = 10
    if image.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image file too large (max {limit_mb} MB).")


def _validate_image_content(image):
    """Verify the uploaded file is a valid image and strip EXIF metadata.

    Uses Pillow to:
    1. Verify it is a real image (not a renamed .exe)
    2. Confirm the format is allowed
    3. Strip EXIF/GPS metadata before saving
    """
    from PIL import Image
    import io

    allowed = {'jpeg', 'png', 'webp'}

    try:
        img = Image.open(image)
        if img.format.lower() not in allowed:
            raise ValidationError(
                f"Unsupported image format: {img.format}. "
                f"Allowed: {', '.join(sorted(allowed))}."
            )

        # Strip EXIF data by re-saving without metadata
        data = list(img.getdata())
        cleaned = Image.new(img.mode, img.size)
        cleaned.putdata(data)

        # Save stripped image into a BytesIO buffer
        buf = io.BytesIO()
        save_format = 'JPEG' if img.format.lower() in ('jpeg', 'jpg') else img.format.upper()
        cleaned.save(buf, format=save_format, quality=85)
        buf.seek(0)

        # Replace the uploaded file content with the cleaned version
        image.file = buf
        image.size = buf.getbuffer().nbytes
    except (IOError, OSError) as e:
        raise ValidationError(f"Invalid or corrupted image file: {e}")


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
    front_image = models.ImageField(
        upload_to='identity_docs/front/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), _validate_image_size, _validate_image_content],
    )
    back_image = models.ImageField(
        upload_to='identity_docs/back/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), _validate_image_size, _validate_image_content],
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.email} - {self.document_type} ({self.document_number})"

