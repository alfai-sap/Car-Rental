from django.contrib import admin

from apps.payments.models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
	list_display = ['invoice_number', 'booking', 'total', 'invoice_status', 'due_date', 'created_at']
	search_fields = ['invoice_number', 'booking__booking_number', 'booking__customer__email']
	list_filter = ['invoice_status', 'created_at', 'due_date']
	readonly_fields = ['invoice_number', 'created_at', 'updated_at', 'total']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ['payment_number', 'booking', 'amount', 'currency', 'provider', 'payment_status', 'paid_at', 'created_at']
	search_fields = ['payment_number', 'provider_reference', 'booking__booking_number', 'booking__customer__email']
	list_filter = ['provider', 'payment_status', 'created_at', 'paid_at']
	readonly_fields = ['payment_number', 'created_at', 'updated_at', 'paid_at', 'raw_payload', 'webhook_event_id']
