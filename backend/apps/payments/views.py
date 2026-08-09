import hashlib
import hmac
import logging
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
from apps.core import services as notify

logger = logging.getLogger(__name__)


def payment_gateway_enabled():
	return (
		settings.PAYMENT_PROVIDER == 'paymongo'
		and bool(settings.PAYMONGO_PUBLIC_KEY)
		and bool(settings.PAYMONGO_SECRET_KEY)
		and bool(settings.PAYMONGO_WEBHOOK_SECRET)
	)


class PaymentCreateSessionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'payment_checkout'

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
                notify.notify_payment_required(booking)
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

        # ── Call PayMongo to create a real checkout session ──
        checkout_url = None
        if payment_gateway_enabled() and payment.provider == Payment.PROVIDER_PAYMONGO:
            try:
                from apps.payments.paymongo import create_checkout_session, PayMongoError

                vehicle_name = f'{booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}'
                description = f'Rental: {vehicle_name} ({booking.pickup_date} – {booking.return_date})'

                result = create_checkout_session(
                    amount=float(invoice.total),
                    currency='PHP',
                    description=description,
                    payment_reference=payment.payment_number,
                    success_url=f'{settings.FRONTEND_URL}/transactions/{booking.id}/?payment=success',
                    cancel_url=f'{settings.FRONTEND_URL}/transactions/{booking.id}/?payment=cancelled',
                    customer_email=booking.customer.email,
                    customer_name=f'{booking.customer.first_name} {booking.customer.last_name}',
                    customer_phone=booking.customer.phone or None,
                )

                checkout_url = result['checkout_url']

                # Store PayMongo references for webhook matching
                payment.provider_reference = result['paymongo_payment_id']
                payment.checkout_url = checkout_url
                payment.save(update_fields=['provider_reference', 'checkout_url', 'updated_at'])

                logger.info(
                    'PayMongo checkout session created for booking %s (payment %s)',
                    booking.booking_number, payment.payment_number,
                )
            except PayMongoError as e:
                logger.error(
                    'PayMongo checkout failed for booking %s: %s',
                    booking.booking_number, e,
                )
                return Response(
                    {'detail': f'Payment provider error: {e}. Please try again.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        return Response({
            'detail': 'Payment session created.',
            'checkout_url': checkout_url,
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
    """Handle PayMongo webhook events.

    Implements HMAC-SHA256 signature verification using the webhook secret
    configured in PAYMONGO_WEBHOOK_SECRET.  Payment status transitions are
    processed inside a database transaction.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        if not payment_gateway_enabled():
            return Response(
                {'detail': 'Payment gateway is not configured yet.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # ── 1. Verify PayMongo webhook signature ──
        signature = request.headers.get('Paymongo-Signature', '')
        if not self._verify_signature(request.body, signature):
            logger.warning('PayMongo webhook: signature verification failed')
            return Response(
                {'detail': 'Invalid webhook signature.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── 2. Extract event data ──
        event_data = request.data.get('data', {})
        event_type = event_data.get('attributes', {}).get('type', '')
        event_id = event_data.get('id', '')

        if not event_id:
            return Response({'detail': 'Missing event ID.'}, status=status.HTTP_400_BAD_REQUEST)

        # ── 3. Idempotency check — don't process the same event twice ──
        if Payment.objects.filter(webhook_event_id=event_id).exists():
            logger.info('PayMongo webhook: duplicate event %s ignored', event_id)
            return Response({'detail': 'Event already processed.'})

        # ── 4. Only handle payment success events ──
        if event_type != 'payment.paid':
            logger.info('PayMongo webhook: unhandled event type %s', event_type)
            return Response({'detail': f'Event type {event_type} acknowledged.'})

        # ── 5. Find the Payment record via the PayMongo payment ID ──
        paymongo_payment_id = event_data.get('id', '')
        payment = Payment.objects.filter(
            provider_reference=paymongo_payment_id,
            payment_status=Payment.STATUS_PENDING,
        ).select_related('booking', 'invoice').first()

        if not payment:
            logger.warning(
                'PayMongo webhook: no pending payment found for reference %s',
                paymongo_payment_id,
            )
            return Response(
                {'detail': 'No matching pending payment found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── 6. Process payment and update booking status ──
        with transaction.atomic():
            payment.payment_status = Payment.STATUS_PAID
            payment.paid_at = timezone.now()
            payment.payment_method = (
                event_data.get('attributes', {})
                .get('payments', [{}])[0]
                .get('source', {})
                .get('type', '')
            )
            payment.raw_payload = request.data
            payment.webhook_event_id = event_id
            payment.save()

            booking = payment.booking
            booking.status = 'confirmed'
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'booked'
                booking.vehicle_unit.save()
            booking.save()

            if payment.invoice:
                payment.invoice.invoice_status = Invoice.STATUS_PAID
                payment.invoice.save()

        notify.notify_payment_successful(booking)
        notify.notify_booking_confirmed(booking)

        logger.info(
            'PayMongo webhook: payment %s confirmed for booking %s',
            payment.payment_number,
            booking.booking_number,
        )

        return Response({'detail': 'Payment processed successfully.'})

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify PayMongo HMAC-SHA256 webhook signature with replay protection.

        PayMongo sends the signature in the format:
            t=<timestamp>,te=,li=<hash>

        The hash is computed as:
            HMAC-SHA256(webhook_secret, "t.te.body")

        We parse the header, extract the timestamp, recompute the HMAC
        using constant-time comparison, AND validate the timestamp is
        within ±5 minutes of the server clock to prevent replay attacks.
        """
        if not signature or not body:
            return False

        # Parse t=X,te=Y,li=Z format
        parts = {}
        for part in signature.split(','):
            key, sep, value = part.partition('=')
            parts[key.strip()] = value.strip() if sep else ''

        timestamp = parts.get('t', '')
        expected_li = parts.get('li', '')

        if not timestamp or not expected_li:
            return False

        # ── Replay-attack protection: reject timestamps older than 5 min ──
        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            return False

        from django.utils import timezone
        now_ts = int(timezone.now().timestamp())
        max_age_seconds = 300  # 5 minutes
        if abs(now_ts - ts) > max_age_seconds:
            logger.warning(
                'PayMongo webhook: timestamp %s is outside ±%ds window (now=%s)',
                ts, max_age_seconds, now_ts,
            )
            return False

        # Recompute HMAC-SHA256(t.te.body) with constant-time comparison
        secret = settings.PAYMONGO_WEBHOOK_SECRET.encode()
        signed_payload = f'{timestamp}.{body.decode()}'.encode()
        computed = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected_li)
