# Consolidated initial migration for the core app.
#
# Creates Notification, AuditLog, RentalDiscountPolicy, and DiscountTier in
# their FINAL state, replacing the previous incremental chain (0001 through
# 0003).
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
        ('payments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('booking_submitted', 'Booking Request Submitted'), ('booking_approved', 'Booking Approved'), ('booking_rejected', 'Booking Rejected'), ('payment_required', 'Payment Required'), ('payment_successful', 'Payment Successful'), ('payment_failed', 'Payment Failed'), ('booking_confirmed', 'Booking Confirmed'), ('reschedule_requested', 'Reschedule Requested'), ('reschedule_approved', 'Reschedule Approved'), ('reschedule_rejected', 'Reschedule Rejected'), ('unit_assigned', 'Vehicle Unit Assigned'), ('unit_changed', 'Vehicle Unit Changed'), ('pickup_reminder', 'Pickup Reminder'), ('rental_activated', 'Rental Activated'), ('extension_requested', 'Extension Requested'), ('extension_approved', 'Extension Approved'), ('extension_rejected', 'Extension Rejected'), ('vehicle_returned', 'Vehicle Returned'), ('additional_payment_required', 'Additional Payment Required'), ('transaction_completed', 'Transaction Completed')], max_length=40)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('is_admin_notification', models.BooleanField(default=False)),
                ('link', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='bookings.booking')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='core_notifi_user_id_1cc5b6_idx'),
                    models.Index(fields=['is_read', 'user'], name='core_notifi_is_read_8bc917_idx'),
                    models.Index(fields=['is_admin_notification', '-created_at'], name='core_notifi_is_admi_433029_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='RentalDiscountPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_default', models.BooleanField(default=False, help_text='The active global policy applied fleet-wide when a vehicle has no explicit override.  Only one policy can be default.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rental discount policy',
                'verbose_name_plural': 'Rental discount policies',
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('booking_approved', 'Booking Approved'), ('booking_rejected', 'Booking Rejected'), ('payment_confirmed', 'Payment Manually Confirmed'), ('rental_activated', 'Rental Activated'), ('rental_completed', 'Rental Completed'), ('unit_assigned', 'Vehicle Unit Assigned'), ('unit_changed', 'Vehicle Unit Changed'), ('booking_cancelled', 'Booking Cancelled'), ('booking_marked_waiting', 'Booking Marked Waiting'), ('profile_updated', 'Profile Updated')], max_length=40)),
                ('summary', models.CharField(max_length=500)),
                ('before_state', models.JSONField(blank=True, default=dict)),
                ('after_state', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='bookings.booking')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='payments.payment')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['-created_at'], name='core_auditl_created_1a76fa_idx'),
                    models.Index(fields=['actor', '-created_at'], name='core_auditl_actor_i_502baf_idx'),
                    models.Index(fields=['booking', '-created_at'], name='core_auditl_booking_c8e46c_idx'),
                    models.Index(fields=['action', '-created_at'], name='core_auditl_action_d80c2d_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='DiscountTier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_days', models.PositiveIntegerField(default=1)),
                ('discount_percent', models.DecimalField(decimal_places=2, default=0, help_text='Discount percentage (0–100) for rentals of min_days or more.', max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100'))])),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tiers', to='core.rentaldiscountpolicy')),
            ],
            options={
                'ordering': ['min_days'],
                'constraints': [
                    models.UniqueConstraint(fields=('policy', 'min_days'), name='core_discounttier_unique_policy_min_days'),
                ],
            },
        ),
    ]
