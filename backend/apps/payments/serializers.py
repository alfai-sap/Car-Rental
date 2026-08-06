from rest_framework import serializers

from apps.payments.models import Invoice, Payment


class InvoiceSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(source='booking.booking_number', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'booking', 'booking_number', 'subtotal',
            'additional_charges', 'discount', 'total', 'invoice_status', 'due_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(source='booking.booking_number', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_number', 'booking', 'booking_number', 'invoice', 'invoice_number',
            'provider', 'provider_reference', 'checkout_url', 'currency', 'amount',
            'payment_method', 'payment_status', 'paid_at', 'raw_payload', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'payment_number', 'created_at', 'updated_at']
