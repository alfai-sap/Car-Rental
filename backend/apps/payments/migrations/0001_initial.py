# Consolidated initial migration for the payments app.
#
# Creates Invoice and Payment in their FINAL state, replacing the previous
# incremental chain (0001 through 0004).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(editable=False, max_length=12, unique=True)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('invoice_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='invoice', to='bookings.booking')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_number', models.CharField(editable=False, max_length=12, unique=True)),
                ('provider', models.CharField(choices=[('disabled', 'Disabled'), ('paymongo', 'PayMongo')], default='disabled', max_length=20)),
                ('provider_reference', models.CharField(blank=True, max_length=120)),
                ('checkout_session_id', models.CharField(blank=True, help_text='PayMongo Checkout Session ID — used to expire the session when the booking is cancelled while payment is pending.', max_length=120)),
                ('checkout_url', models.URLField(blank=True)),
                ('currency', models.CharField(default='PHP', max_length=3)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('payment_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('expired', 'Expired'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('raw_payload', models.JSONField(blank=True, default=dict)),
                ('webhook_event_id', models.CharField(blank=True, help_text='PayMongo event ID for idempotency — prevents double-processing of webhooks.', max_length=100, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='bookings.booking')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='payments.invoice')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
