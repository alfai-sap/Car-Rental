# Consolidated initial migration for the bookings app.
#
# This single migration creates the Booking and AssignmentHistory models in
# their FINAL state, replacing the previous incremental chain of migrations
# (0001 through 0013).  Migrating from scratch applies only this file —
# no intermediate add/remove/alter steps are replayed.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vehicles', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking_number', models.CharField(editable=False, max_length=12, unique=True)),
                ('pickup_date', models.DateField()),
                ('return_date', models.DateField()),
                ('pickup_time', models.TimeField()),
                ('return_time', models.TimeField(default='17:00')),
                ('rental_days', models.PositiveSmallIntegerField()),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_percent', models.DecimalField(decimal_places=2, default=0, help_text='Discount percentage applied to this booking (snapshot at booking time).', max_digits=5)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, help_text='Monetary discount applied to this booking (snapshot at booking time).', max_digits=10)),
                ('estimated_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('awaiting_payment', 'Awaiting Payment'), ('confirmed', 'Confirmed'), ('waiting_for_pickup', 'Waiting for Pickup'), ('active', 'Active Rental'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('rejected', 'Rejected')], default='pending_approval', max_length=20)),
                ('special_request', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('cancellation_reason', models.TextField(blank=True)),
                ('handover_time', models.DateTimeField(blank=True, null=True)),
                ('return_time_actual', models.DateTimeField(blank=True, null=True)),
                ('return_unit_status', models.CharField(blank=True, choices=[('available', 'Available'), ('maintenance', 'Maintenance'), ('inactive', 'Inactive')], help_text='Post-return status of the vehicle unit (available/maintenance/inactive). Must be recorded before completing the transaction.', max_length=20)),
                ('identity_snapshot', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to=settings.AUTH_USER_MODEL)),
                ('vehicle', models.ForeignKey(help_text='Original vehicle.  Deleting a vehicle that is referenced by a booking is blocked.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='vehicles.vehicle')),
                ('vehicle_unit', models.ForeignKey(blank=True, help_text='Assigned unit.  Deleting a unit referenced by a booking is blocked.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='vehicles.vehicleunit')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AssignmentHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignment_history', to='bookings.booking')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='unit_assignments', to=settings.AUTH_USER_MODEL)),
                ('new_unit', models.ForeignKey(help_text='Assigned unit.  Deleting a unit referenced by assignment history is blocked.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='new_assignments', to='vehicles.vehicleunit')),
                ('previous_unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='previous_assignments', to='vehicles.vehicleunit')),
            ],
            options={
                'verbose_name_plural': 'Assignment histories',
                'ordering': ['-created_at'],
            },
        ),
    ]
