from django.db import models


class Vehicle(models.Model):
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
