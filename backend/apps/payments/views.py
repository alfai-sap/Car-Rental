from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.payments.models import Invoice, Payment


def payment_gateway_enabled():
	return (
		settings.PAYMENT_PROVIDER == 'paymongo'
		and bool(settings.PAYMONGO_PUBLIC_KEY)
		and bool(settings.PAYMONGO_SECRET_KEY)
		and bool(settings.PAYMONGO_WEBHOOK_SECRET)
	)


class PaymentCreateSessionView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		booking_id = request.data.get('booking_id')
		if not booking_id:
			return Response({'detail': 'booking_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

		booking = get_object_or_404(
			Booking.objects.select_related('customer', 'vehicle'),
			pk=booking_id,
		)

		if booking.customer_id != request.user.id and not request.user.is_staff:
			return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

		if booking.status not in ['approved', 'awaiting_payment']:
			return Response(
				{'detail': 'Booking must be awaiting payment before checkout can be created.'},
				status=status.HTTP_400_BAD_REQUEST,
			)

		with transaction.atomic():
			# Transition from approved → awaiting_payment if needed
			if booking.status == 'approved':
				booking.status = 'awaiting_payment'
				booking.save()
			invoice, _ = Invoice.objects.get_or_create(
				booking=booking,
				defaults={
					'subtotal': booking.subtotal,
					'additional_charges': 0,
					'discount': 0,
					'total': booking.estimated_total,
					'invoice_status': Invoice.STATUS_PENDING,
					'due_date': timezone.now().date() + timedelta(days=3),
				},
			)

			payment = Payment.objects.create(
				booking=booking,
				invoice=invoice,
				provider=Payment.PROVIDER_PAYMONGO if payment_gateway_enabled() else Payment.PROVIDER_DISABLED,
				amount=invoice.total,
				currency='PHP',
				payment_status=Payment.STATUS_PENDING,
			)

		return Response({
			'detail': 'Payment setup is not configured yet. Configure the payment provider to enable checkout.',
			'checkout_url': None,
			'payment': {
				'id': payment.id,
				'payment_number': payment.payment_number,
				'payment_status': payment.payment_status,
			},
			'invoice': {
				'id': invoice.id,
				'invoice_number': invoice.invoice_number,
				'invoice_status': invoice.invoice_status,
				'total': str(invoice.total),
			},
		})


class PaymentDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, pk):
		payment = get_object_or_404(Payment.objects.select_related('booking', 'invoice'), pk=pk)
		if payment.booking.customer_id != request.user.id and not request.user.is_staff:
			return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
		return Response({
			'id': payment.id,
			'payment_number': payment.payment_number,
			'booking': payment.booking_id,
			'invoice': payment.invoice_id,
			'provider': payment.provider,
			'provider_reference': payment.provider_reference,
			'checkout_url': payment.checkout_url or None,
			'currency': payment.currency,
			'amount': str(payment.amount),
			'payment_method': payment.payment_method,
			'payment_status': payment.payment_status,
			'paid_at': payment.paid_at,
			'created_at': payment.created_at,
			'updated_at': payment.updated_at,
		})


class PaymentHistoryView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		queryset = Payment.objects.select_related('booking', 'invoice').order_by('-created_at')
		if not request.user.is_staff:
			queryset = queryset.filter(booking__customer=request.user)

		return Response([
			{
				'id': payment.id,
				'payment_number': payment.payment_number,
				'booking': payment.booking_id,
				'booking_number': payment.booking.booking_number,
				'invoice_number': payment.invoice.invoice_number if payment.invoice else None,
				'provider': payment.provider,
				'amount': str(payment.amount),
				'currency': payment.currency,
				'payment_status': payment.payment_status,
				'paid_at': payment.paid_at,
				'created_at': payment.created_at,
				'updated_at': payment.updated_at,
			}
			for payment in queryset
		])


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not payment_gateway_enabled():
            return Response(
                {'detail': 'Payment gateway is not configured yet.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # TODO(Phase 7): Verify PayMongo webhook signature using PAYMONGO_WEBHOOK_SECRET
        # before processing the payment status update. See PayMongo webhook docs.
        return Response(
            {'detail': 'Webhook endpoint ready. Signature verification will be implemented in Payment Phase.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
