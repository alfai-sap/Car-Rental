# Consolidated initial migration for the vehicles app.
#
# Creates Vehicle, VehicleImage, and VehicleUnit in their FINAL state.
# Vehicle.discount_policy is intentionally NOT created here: it references
# core.RentalDiscountPolicy, and core depends on bookings which depends on
# vehicles — a schema cycle.  The FK is added in 0002 after core exists.
import apps.core.validators
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('make', models.CharField(max_length=50)),
                ('model', models.CharField(max_length=50)),
                ('year', models.PositiveIntegerField()),
                ('type', models.CharField(choices=[('sedan', 'Sedan'), ('suv', 'SUV'), ('hatchback', 'Hatchback'), ('mpv', 'MPV'), ('van', 'Van'), ('pickup', 'Pickup'), ('truck', 'Truck'), ('coupe', 'Coupe'), ('convertible', 'Convertible'), ('wagon', 'Wagon')], default='sedan', max_length=30)),
                ('transmission', models.CharField(choices=[('automatic', 'Automatic'), ('manual', 'Manual')], default='automatic', max_length=15)),
                ('fuel', models.CharField(choices=[('gasoline', 'Gasoline'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')], default='gasoline', max_length=15)),
                ('seats', models.PositiveSmallIntegerField(default=5)),
                ('price_per_day', models.DecimalField(decimal_places=2, help_text='Daily rental price (must be greater than 0).', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('status', models.CharField(choices=[('available', 'Available'), ('unavailable', 'Unavailable')], default='available', max_length=15)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VehicleImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='vehicles/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), apps.core.validators.validate_image_size, apps.core.validators.validate_image_content])),
                ('is_primary', models.BooleanField(default=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='vehicles.vehicle')),
            ],
            options={
                'ordering': ['-is_primary', '-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='VehicleUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plate_number', models.CharField(help_text='Format: ABC-1234 or ABC-123 (3 letters, dash, 3-4 digits).', max_length=20, unique=True)),
                ('status', models.CharField(choices=[('available', 'Available'), ('reserved', 'Reserved'), ('booked', 'Booked'), ('active_rental', 'Active Rental'), ('maintenance', 'Maintenance'), ('inactive', 'Inactive')], default='available', max_length=20)),
                ('mileage', models.PositiveIntegerField(blank=True, default=0)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='vehicles.vehicle')),
            ],
            options={
                'ordering': ['plate_number'],
            },
        ),
        migrations.AddConstraint(
            model_name='vehicleunit',
            constraint=models.CheckConstraint(condition=models.Q(('plate_number__regex', '^[A-Z]{3}-\\d{3,4}$')), name='vehicles_vehicleunit_plate_number_format'),
        ),
    ]
