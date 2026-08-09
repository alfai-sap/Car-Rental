from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def _validate_image_content(image):
    """Verify the uploaded file is a valid image and strip EXIF metadata."""
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

        # Strip EXIF data
        data = list(img.getdata())
        cleaned = Image.new(img.mode, img.size)
        cleaned.putdata(data)

        buf = io.BytesIO()
        save_format = 'JPEG' if img.format.lower() in ('jpeg', 'jpg') else img.format.upper()
        cleaned.save(buf, format=save_format, quality=85)
        buf.seek(0)

        image.file = buf
        image.size = buf.getbuffer().nbytes
    except (IOError, OSError) as e:
        raise ValidationError(f"Invalid or corrupted image file: {e}")


def _validate_image_size(image):
    """Reject images larger than 10 MB."""
    limit_mb = 10
    if image.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image file too large (max {limit_mb} MB).")


class Vehicle(models.Model):
    """Represents a vehicle model listing displayed to customers.

    Availability is determined per VehicleUnit — this model stores shared
    listing info (make, model, price, images) while VehicleUnit tracks
    per-unit status (available, reserved, booked, active_rental, etc.).
    The 'status' field here is deprecated and only retained for seed data
    compatibility. Always use VehicleUnit to determine real availability.
    """
    TRANSMISSION_CHOICES = [
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ]

    FUEL_CHOICES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ]

    VEHICLE_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('mpv', 'MPV'),
        ('van', 'Van'),
        ('pickup', 'Pickup'),
        ('truck', 'Truck'),
        ('coupe', 'Coupe'),
        ('convertible', 'Convertible'),
        ('wagon', 'Wagon'),
    ]

    make = models.CharField(max_length=50)          # e.g. Toyota, Honda
    model = models.CharField(max_length=50)          # e.g. Vios, Civic
    year = models.PositiveIntegerField()
    type = models.CharField(max_length=30, choices=VEHICLE_TYPE_CHOICES, default='sedan')
    transmission = models.CharField(max_length=15, choices=TRANSMISSION_CHOICES, default='automatic')
    fuel = models.CharField(max_length=15, choices=FUEL_CHOICES, default='gasoline')
    seats = models.PositiveSmallIntegerField(default=5)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='available')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.status})"


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='vehicles/',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
            _validate_image_size,
            _validate_image_content,
        ],
    )
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-uploaded_at']

    def __str__(self):
        return f"Image for {self.vehicle} {'(primary)' if self.is_primary else ''}"


class VehicleUnit(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
        ('active_rental', 'Active Rental'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='units')
    plate_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    mileage = models.PositiveIntegerField(default=0, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['plate_number']

    def __str__(self):
        return f"{self.plate_number} — {self.vehicle} ({self.get_status_display()})"
