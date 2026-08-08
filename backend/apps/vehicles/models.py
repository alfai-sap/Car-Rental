from django.db import models


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
        ('rented', 'Rented'),
        ('maintenance', 'Maintenance'),
        ('retired', 'Retired'),
    ]

    make = models.CharField(max_length=50)          # e.g. Toyota, Honda
    model = models.CharField(max_length=50)          # e.g. Vios, Civic
    year = models.PositiveIntegerField()
    type = models.CharField(max_length=30)           # e.g. Sedan, SUV, Hatchback
    # Note: blank=False is the default for CharField; fields with blank=True
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
    image = models.ImageField(upload_to='vehicles/')
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
