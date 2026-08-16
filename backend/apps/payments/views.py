import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
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


class PaymentAmountMismatchError(Exception):
    """Raised when a gateway payment amount/currency does not match the invoice."""


def payment_gateway_enabled():
    return (
        settings.PAYMENT_PROVIDER == 'paymongo'
        and bool(settings.PAYMONGO_PUBLIC_KEY)
        and bool(settings.PAYMONGO_SECRET_KEY)
        and bool(settings.PAYMONGO_WEBHOOK_SECRET)
    )


def finalize_paid_payment(payment, *, amount_cents, currency, payment_method='', webhook_event_id=None):
    """Apply a confirmed gateway payment to the local records.

    Shared by the webhook and the reconciliation command so both paths
    enforce the exact same amount/currency verification and booking
    state transition.  Never resurrects a booking that is no longer
    awaiting payment.

    Raises PaymentAmountMismatchError when the gateway amount/currency
    does not match the invoice (the caller decides how to respond).
    """
    booking = payment.booking

    expected_cents = None
    if payment.invoice:
        expected_cents = int(payment.invoice.total * 100)

    if currency != 'PHP' or (expected_cents is not None and amount_cents != expected_cents):
        raise PaymentAmountMismatchError(
            f'expected {expected_cents} PHP, got {amount_cents} {currency}'
        )

    payment.payment_status = Payment.STATUS_PAID
    payment.paid_at = timezone.now()
    payment.payment_method = payment_method or ''
    if webhook_event_id:
        payment.webhook_event_id = webhook_event_id

    try:
        with transaction.atomic():
            payment.save()
            if payment.invoice:
                payment.invoice.invoice_status = Invoice.STATUS_PAID
                payment.invoice.save()
            # Only advance the booking if it is still awaiting payment.
            # A customer could complete payment after the booking was
            # cancelled/rejected; never resurrect it.
            if booking.status == 'awaiting_payment':
                booking.status = 'confirmed'
                if booking.vehicle_unit:
                    booking.vehicle_unit.status = 'booked'
                    booking.vehicle_unit.save()
                booking.save()
    except IntegrityError:
        raise

    if booking.status == 'confirmed':
        notify.notify_payment_successful(booking)
        notify.notify_booking_confirmed(booking)
    else:
        # Payment arrived for a booking that is no longer active
        # (e.g. it was cancelled/rejected while the customer was on
        # the PayMongo page).  Never send a "Booking Finalized" email
        # for a booking that was never finalized — alert support
        # instead so a refund can be arranged.
        notify.notify_payment_received_inactive(booking)

    return booking


def reconcile_payment(payment):
    """Reconcile a single pending payment against the gateway.

    Used by both the ``reconcile_payments`` command and the booking
    ``check-payment`` action so the customer/admin can force a refresh of a
    booking whose webhook was missed.  Resolves via ``provider_reference``
    when present, otherwise via the checkout session's embedded payments.

    Returns the finalised booking on a successful paid transition, or None
    when there is nothing to do (still pending / failed / expired / error).
    """
    from apps.payments.paymongo import (
        PayMongoError,
        retrieve_checkout_session,
        retrieve_payment,
    )

    payment_attrs = None
    if payment.provider_reference:
        try:
            payment_attrs = retrieve_payment(payment.provider_reference)
        except PayMongoError as exc:
            logger.warning('reconcile_payment %s: retrieval failed (%s)', payment.payment_number, exc)
            return None
    elif payment.checkout_session_id:
        try:
            session_attrs = retrieve_checkout_session(payment.checkout_session_id)
        except PayMongoError as exc:
            logger.warning('reconcile_payment %s: checkout session retrieval failed (%s)', payment.payment_number, exc)
            return None

        session_payments = session_attrs.get('payments', []) or []
        gateway_payment = session_payments[0] if session_payments else None
        if gateway_payment:
            gateway_id = gateway_payment.get('id', '')
            if gateway_id and not payment.provider_reference:
                payment.provider_reference = gateway_id
                payment.save(update_fields=['provider_reference', 'updated_at'])
            payment_attrs = gateway_payment.get('attributes') or {}

    if payment_attrs is None:
        logger.warning('reconcile_payment %s: no gateway reference', payment.payment_number)
        return None

    status = (payment_attrs.get('status') or '').lower()
    amount_cents = payment_attrs.get('amount')
    currency = (payment_attrs.get('currency') or '').upper()
    payment_method = payment_attrs.get('source', {}).get('type', '')

    if status == 'paid':
        try:
            return finalize_paid_payment(
                payment,
                amount_cents=amount_cents,
                currency=currency,
                payment_method=payment_method,
            )
        except PaymentAmountMismatchError as exc:
            logger.error('reconcile_payment %s: amount mismatch (%s)', payment.payment_number, exc)
            return None
    elif status == 'failed':
        payment.payment_status = Payment.STATUS_FAILED
        payment.save(update_fields=['payment_status', 'updated_at'])
    elif status == 'expired':
        payment.payment_status = Payment.STATUS_EXPIRED
        payment.save(update_fields=['payment_status', 'updated_at'])

    return None


def expire_pending_payments(booking):
    """Expire every live checkout session for a booking and mark the local
    Payment records cancelled.

    Called when a booking is cancelled so the customer can no longer
    complete payment on the hosted checkout page.  The PayMongo call is
    best-effort: if the gateway is unreachable the local payment is still
    marked cancelled, and the webhook's "never resurrect a cancelled
    booking" guard remains the final line of defense.
    """
    from apps.payments.paymongo import expire_checkout_session

    pending_payments = Payment.objects.filter(
        booking=booking,
        payment_status=Payment.STATUS_PENDING,
    )
    for payment in pending_payments:
        if payment.checkout_session_id:
            expire_checkout_session(payment.checkout_session_id)
        payment.payment_status = Payment.STATUS_CANCELLED
        payment.save(update_fields=['payment_status', 'updated_at'])

    # The invoice must mirror the payment: a cancelled booking with no
    # payable amount should not leave a dangling 'pending' invoice.
    invoice = Invoice.objects.filter(booking=booking).first()
    if invoice and invoice.invoice_status == Invoice.STATUS_PENDING:
        invoice.invoice_status = Invoice.STATUS_CANCELLED
        invoice.save(update_fields=['invoice_status', 'updated_at'])


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

        checkout_url = None
        provider = Payment.PROVIDER_PAYMONGO if payment_gateway_enabled() else Payment.PROVIDER_DISABLED

        # ── Idempotency: reuse an existing open checkout ──
        # Re-attempts must not create duplicate PayMongo sessions (each with
        # its own live checkout URL) for the same booking.  Only an unexpired
        # PENDING payment still has a live checkout URL worth reusing.
        # FAILED and EXPIRED payments are superseded — a customer whose
        # payment failed, or whose checkout expired, can simply retry to get
        # a fresh session, so we fall through and create a new one.
        existing_payment = Payment.objects.filter(
            booking=booking,
            payment_status=Payment.STATUS_PENDING,
            provider=provider,
        ).select_related('invoice').order_by('-created_at').first()

        if existing_payment and existing_payment.checkout_url:
            return Response({
                'detail': 'An active payment session already exists for this booking.',
                'checkout_url': existing_payment.checkout_url,
                'payment': {
                    'id': existing_payment.id,
                    'payment_number': existing_payment.payment_number,
                    'payment_status': existing_payment.payment_status,
                },
                'invoice': {
                    'id': existing_payment.invoice_id,
                    'invoice_number': existing_payment.invoice.invoice_number if existing_payment.invoice else None,
                    'invoice_status': existing_payment.invoice.invoice_status if existing_payment.invoice else None,
                    'total': str(existing_payment.invoice.total) if existing_payment.invoice else None,
                },
            })

        # ── Determine the exact amount to charge ──
        # It must equal what the webhook later verifies (invoice.total),
        # which is the booking's immutable pricing snapshot (subtotal minus
        # any discount).
        charge_amount = booking.estimated_total

        # ── Call PayMongo FIRST before any DB writes ──
        # This prevents the booking from being left in 'awaiting_payment'
        # with no checkout URL if the PayMongo API is unreachable.
        paymongo_result = None
        if provider == Payment.PROVIDER_PAYMONGO:
            try:
                from apps.payments.paymongo import create_checkout_session, PayMongoError

                from apps.core.ids import encode_id

                vehicle_name = f'{booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}'
                description = f'Rental: {vehicle_name} ({booking.pickup_date} – {booking.return_date})'
                booking_hash_id = encode_id('booking', booking.id)

                paymongo_result = create_checkout_session(
                    amount=charge_amount,
                    currency='PHP',
                    description=description,
                    payment_reference=f'PMT-{booking.booking_number}',
                    success_url=f'{settings.FRONTEND_URL}/transactions/{booking_hash_id}/?payment=success',
                    cancel_url=f'{settings.FRONTEND_URL}/transactions/{booking_hash_id}/?payment=cancelled',
                    customer_email=booking.customer.email,
                    customer_name=f'{booking.customer.first_name} {booking.customer.last_name}',
                    customer_phone=booking.customer.phone or None,
                )
                checkout_url = paymongo_result['checkout_url']
            except PayMongoError as e:
                logger.error(
                    'PayMongo checkout failed for booking %s: %s',
                    booking.booking_number, e,
                )
                return Response(
                    {'detail': f'Payment provider error: {e}. Please try again.'},
                    status=status.HTTP_502_BAD_GATEWAY,
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
                    'discount': booking.discount_amount,
                    'total': booking.estimated_total,
                    'invoice_status': Invoice.STATUS_PENDING,
                    'due_date': timezone.now().date() + timedelta(days=3),
                },
            )
            # Keep the rental discount/subtotal in sync with the booking's
            # immutable pricing snapshot on re-attempts.  Invoice.save()
            # recomputes `total = subtotal - discount`.
            if invoice.invoice_status != Invoice.STATUS_PAID:
                invoice.subtotal = booking.subtotal
                invoice.discount = booking.discount_amount
                invoice.save(update_fields=['subtotal', 'discount', 'total', 'updated_at'])

            # The PayMongo session amount and the stored Payment.amount must
            # match what the webhook will verify (invoice.total).  In practice
            # the initial amount equals invoice.total because the booking's
            # pricing snapshot is the sole source of truth for the charge.
            payment = Payment.objects.create(
                booking=booking,
                invoice=invoice,
                provider=provider,
                amount=invoice.total,
                currency='PHP',
                payment_status=Payment.STATUS_PENDING,
            )

            if paymongo_result:
                payment.provider_reference = paymongo_result['paymongo_payment_id']
                payment.checkout_session_id = paymongo_result.get('session_id', '')
                payment.checkout_url = checkout_url
                payment.save(update_fields=['provider_reference', 'checkout_session_id', 'checkout_url', 'updated_at'])
                logger.info(
                    'PayMongo checkout session created for booking %s (payment %s)',
                    booking.booking_number, payment.payment_number,
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
                'invoice_total': str(payment.invoice.total) if payment.invoice else None,
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

    Handles the hosted-checkout event ``checkout_session.payment.paid`` (the
    primary path for this app) as well as the Payment Intents events
    ``payment.paid`` and ``payment.failed``.  Payload parsing accepts both the
    legacy JSON:API envelope and PayMongo's current envelope shape.
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

        # ── 2. Extract event data (supports both PayMongo payload shapes) ──
        # PayMongo has shipped two webhook envelopes:
        #   legacy JSON:API — data.attributes.type / data.attributes.data
        #   current        — data.type            / data.data
        # Normalize both so either shape is handled correctly.
        event_data = request.data.get('data', {})
        event_attributes = event_data.get('attributes') or {}
        event_type = event_attributes.get('type', '') or event_data.get('type', '')
        resource = event_data.get('data') or event_attributes.get('data', {})
        # Current shape has no top-level event id — fall back to the resource
        # id (checkout session / payment id) so idempotency still works.
        event_id = event_data.get('id', '') or resource.get('id', '')

        if not event_id:
            return Response({'detail': 'Missing event ID.'}, status=status.HTTP_400_BAD_REQUEST)

        # ── 3. Idempotency check — don't process the same event twice ──
        if Payment.objects.filter(webhook_event_id=event_id).exists():
            logger.info('PayMongo webhook: duplicate event %s ignored', event_id)
            return Response({'detail': 'Event already processed.'})

        # ── 4. Dispatch by event type ──
        # Hosted Checkout emits `checkout_session.payment.paid`; the Payment
        # Intents flow emits `payment.paid`/`payment.failed`.  (PayMongo no
        # longer exposes `payment.expired` or `checkout_session.expired` —
        # expiry is handled by the reconciliation command + fresh retry.)
        handled_types = {'payment.paid', 'checkout_session.payment.paid', 'payment.failed'}
        if event_type not in handled_types:
            logger.info('PayMongo webhook: unhandled event type %s', event_type)
            return Response({'detail': f'Event type {event_type} acknowledged.'})

        # ── 5. Find the Payment record and its gateway-side attributes ──
        if event_type == 'checkout_session.payment.paid':
            # The resource is a Checkout Session; the payment (and its
            # amount/currency/source) is nested under attributes.payments[].
            session_id = resource.get('id', '')
            payment = None
            payment_attributes = None
            gateway_payments = (resource.get('attributes') or {}).get('payments', [])
            for gateway_payment in gateway_payments:
                gateway_id = gateway_payment.get('id', '')
                candidate = Payment.objects.filter(
                    provider_reference=gateway_id,
                    payment_status=Payment.STATUS_PENDING,
                ).select_related('booking', 'invoice').first()
                if candidate:
                    payment = candidate
                    payment_attributes = gateway_payment.get('attributes') or {}
                    break
            # v1 checkout sessions don't expose a payment id at creation time,
            # so fall back to matching the booking's pending payment by its
            # checkout_session_id (set when the session was created).
            if payment is None and session_id:
                payment = Payment.objects.filter(
                    checkout_session_id=session_id,
                    payment_status=Payment.STATUS_PENDING,
                ).select_related('booking', 'invoice').first()
                if payment:
                    # The gateway payment attrs are the first paid entry.
                    paid_entry = next(
                        (p for p in gateway_payments
                         if ((p.get('attributes') or {}).get('status') or '').lower() == 'paid'),
                        gateway_payments[0] if gateway_payments else None,
                    )
                    payment_attributes = (paid_entry or {}).get('attributes') or {}
        else:
            paymongo_payment_id = resource.get('id', '')
            payment = Payment.objects.filter(
                provider_reference=paymongo_payment_id,
                payment_status=Payment.STATUS_PENDING,
            ).select_related('booking', 'invoice').first()
            payment_attributes = resource.get('attributes') or {}

        if not payment:
            logger.warning(
                'PayMongo webhook: no pending payment found for event %s (%s)',
                event_type, event_id,
            )
            return Response(
                {'detail': 'No matching pending payment found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        booking = payment.booking
        payment.raw_payload = request.data
        payment.webhook_event_id = event_id

        if event_type in ('payment.paid', 'checkout_session.payment.paid'):
            # ── Amount/currency verification + state transition ──
            paid_amount_cents = payment_attributes.get('amount')
            paid_currency = (payment_attributes.get('currency') or '').upper()
            payment_method = payment_attributes.get('source', {}).get('type', '')

            try:
                booking = finalize_paid_payment(
                    payment,
                    amount_cents=paid_amount_cents,
                    currency=paid_currency,
                    payment_method=payment_method,
                    webhook_event_id=event_id,
                )
            except PaymentAmountMismatchError as exc:
                logger.error(
                    'PayMongo webhook: amount mismatch for payment %s (%s)',
                    payment.payment_number, exc,
                )
                return Response(
                    {'detail': 'Payment amount does not match the invoice.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except IntegrityError:
                logger.info('PayMongo webhook: duplicate event %s (already recorded)', event_id)
                return Response({'detail': 'Event already processed.'})

            logger.info(
                'PayMongo webhook: payment %s confirmed for booking %s',
                payment.payment_number, booking.booking_number,
            )
            return Response({'detail': 'Payment processed successfully.'})

        elif event_type == 'payment.failed':
            try:
                with transaction.atomic():
                    payment.payment_status = Payment.STATUS_FAILED
                    payment.save()
                    # Booking stays in awaiting_payment so customer can retry
            except IntegrityError:
                logger.info('PayMongo webhook: duplicate event %s (already recorded)', event_id)
                return Response({'detail': 'Event already processed.'})

            notify.notify_payment_failed(booking)
            logger.info(
                'PayMongo webhook: payment %s failed for booking %s',
                payment.payment_number, booking.booking_number,
            )
            return Response({'detail': 'Payment failure recorded.'})

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
        expiry = parts.get('te', '')
        expected_li = parts.get('li', '')

        if not timestamp or not expiry or not expected_li:
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

        # ── Expiry enforcement ──
        # PayMongo sends te=<expiry>.  Reject signatures that have expired.
        try:
            te = int(expiry)
        except (TypeError, ValueError):
            return False
        if te < now_ts:
            logger.warning(
                'PayMongo webhook: signature expiry %s is in the past (now=%s)',
                te, now_ts,
            )
            return False

        # Recompute HMAC-SHA256(t.te.body) with constant-time comparison.
        # This matches PayMongo's official signing format.
        secret = settings.PAYMONGO_WEBHOOK_SECRET.encode()
        signed_payload = f'{timestamp}.{expiry}.{body.decode()}'.encode()
        computed = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, expected_li)
