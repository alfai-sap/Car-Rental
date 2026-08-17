import logging
import os
import uuid as uuid_lib

from django.core.files.base import ContentFile
from django.core.signing import SignatureExpired, BadSignature
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.bookings.models import Booking, AssignmentHistory
from apps.bookings.serializers import (
    BookingSerializer, BookingStatusUpdateSerializer,
    DashboardBookingSerializer, AdminDashboardBookingSerializer,
    AssignmentHistorySerializer,
)
from apps.core import services as notify
from apps.core.services import create_audit_log, compute_rental_pricing
from apps.core.ids import HashedIdLookupMixin
from apps.core.storage import private_identity_storage
from apps.core.throttles import IdentityImageThrottle
from apps.vehicles.models import Vehicle, VehicleUnit, UNIT_UNAVAILABLE_STATUSES

logger = logging.getLogger(__name__)


# ── Booking-reserving statuses ──
# Only these statuses occupy a VehicleUnit and block availability.
UNIT_OCCUPYING_STATUSES = ['approved', 'awaiting_payment', 'confirmed', 'waiting_for_pickup', 'active']


# ── Identity snapshot image storage ──
# Snapshot images are immutable copies stored separately from the live
# profile documents so that editing identity documents later does NOT
# mutate completed transaction records.
SNAPSHOT_IMAGE_DIR = 'identity_docs/snapshots'


def _copy_snapshot_image(image_field):
    """Copy an uploaded identity image into the private snapshot directory.

    Returns the relative storage name of the copy, or None on failure.
    The copy is immutable — it is never touched by profile edits — and lives
    in the private identity storage, never in the public MEDIA_ROOT.
    """
    try:
        storage = private_identity_storage()
        ext = os.path.splitext(image_field.name)[1] or '.jpg'
        name = f'{SNAPSHOT_IMAGE_DIR}/{uuid_lib.uuid4().hex}{ext}'
        with image_field.open('rb') as fh:
            content = fh.read()
        storage.save(name, ContentFile(content))
        return name
    except Exception as e:
        logger.exception('Failed to copy identity snapshot image: %s', e)
        return None


def _build_identity_snapshot(user):
    """Capture full customer profile AND identity document values — including
    immutable copies of the document photo files — as a JSON snapshot.

    This snapshot is stored on the booking and is the sole source of truth
    for what a transaction looked like at booking time.  Later changes to
    the customer's profile or identity documents never affect it.
    """
    docs = user.identity_documents.all()
    documents = []
    for idx, doc in enumerate(docs):
        documents.append({
            'id': doc.id,
            'document_type': doc.document_type,
            'document_number': doc.document_number,
            'front_image': _copy_snapshot_image(doc.front_image) if doc.front_image else None,
            'back_image': _copy_snapshot_image(doc.back_image) if doc.back_image else None,
            'index': idx,
        })
    return {
        'customer_name': f"{user.first_name} {user.last_name}",
        'customer_email': user.email,
        'customer_phone': user.phone,
        'pickup_address': _current_pickup_address(),
        'documents': documents,
        'captured_at': timezone.now().isoformat(),
    }


def _current_pickup_address():
    """Return the global pickup address at booking time (for snapshotting)."""
    from apps.core.models import PickupAddress
    return PickupAddress.get_instance().address or None


# ─────────────────────────────────────────────
#  Booking ViewSet
# ─────────────────────────────────────────────

class BookingViewSet(HashedIdLookupMixin, viewsets.ModelViewSet):
    hashed_id_model_name = 'booking'
    queryset = Booking.objects.select_related(
        'customer', 'vehicle', 'vehicle_unit',
    ).prefetch_related(
        'vehicle__images', 'customer__identity_documents',
    )
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['vehicle', 'status']
    ordering_fields = ['created_at', 'pickup_date']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(customer=user)

    def perform_create(self, serializer):
        with transaction.atomic():
            # ── Defense in depth: re-check booking eligibility server-side ──
            # The serializer already validates this, but enforcing here
            # guarantees no booking is created without verified email,
            # complete profile, and identity documents on file.
            customer = self.request.user
            if not customer.is_booking_eligible():
                raise serializers.ValidationError({
                    'detail': 'You are not eligible to book. Verify your email, complete your profile, and upload identity documents.',
                })

            # Lock the vehicle record to prevent race conditions during
            # availability checks (SELECT … FOR UPDATE).
            # The locked row MUST be held in a variable — otherwise the
            # lock is released immediately when the queryset is discarded.
            vehicle = serializer.validated_data['vehicle']
            locked_vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)

            pickup_date = serializer.validated_data['pickup_date']
            return_date = serializer.validated_data['return_date']

            # Re-check availability inside the lock to close the TOCTOU window
            # between serializer.validate() and the atomic block.
            total = VehicleUnit.objects.filter(vehicle=locked_vehicle).count()
            if total == 0:
                raise serializers.ValidationError({
                    'vehicle': 'No units available for this vehicle. Please contact the administrator.',
                })

            booked_unit_ids = Booking.objects.filter(
                vehicle=locked_vehicle,
                vehicle_unit__isnull=False,
                status__in=UNIT_OCCUPYING_STATUSES,
                pickup_date__lt=return_date,
                return_date__gt=pickup_date,
            ).values_list('vehicle_unit_id', flat=True)

            unavailable_ids = VehicleUnit.objects.filter(
                vehicle=locked_vehicle, status__in=UNIT_UNAVAILABLE_STATUSES,
            ).values_list('id', flat=True)

            blocked = set(booked_unit_ids) | set(unavailable_ids)
            available = total - VehicleUnit.objects.filter(
                vehicle=locked_vehicle, id__in=blocked,
            ).count()

            if available <= 0:
                raise serializers.ValidationError({
                    'vehicle': 'No units available for the selected dates.',
                })

            snapshot = _build_identity_snapshot(self.request.user)

            booking = serializer.save(
                customer=self.request.user,
                vehicle_unit=None,  # Admin assigns unit after approval
                identity_snapshot=snapshot,
            )

        notify.notify_booking_submitted(booking)

    def get_serializer_class(self):
        if self.action in ('approve', 'reject'):
            return BookingStatusUpdateSerializer
        return BookingSerializer

    def destroy(self, request, *args, **kwargs):
        """Bookings are financial/audit records and must not be deleted.

        Customers and staff should use the cancel flow instead.
        """
        return Response(
            {'detail': 'Bookings cannot be deleted. Use the cancel flow instead.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # ── Customer actions ──

    def get_throttles(self):
        """Apply the payment-checkout throttle to the ``check-payment`` action.

        ``check_payment`` triggers an outbound PayMongo API call per request,
        so it must be rate-limited like the checkout endpoint itself.  The
        ScopedRateThrottle in DEFAULT_THROTTLE_CLASSES reads
        ``view.throttle_scope`` at request time, so setting it here scopes
        exactly this action without throttling other booking endpoints.
        """
        if self.action == 'check_payment':
            self.throttle_scope = 'payment_checkout'
        return super().get_throttles()

    @action(detail=True, methods=['post'], url_path='check-payment')
    def check_payment(self, request, pk=None):
        """Re-check a pending payment against the gateway.

        Used by the frontend after the customer returns from the hosted
        checkout page.  If the webhook was missed or is still in flight, this
        queries PayMongo directly and finalises the booking so the UI reflects
        the real state immediately.
        """
        booking = self.get_object()
        if booking.customer != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.payments.models import Payment
        from apps.payments.views import reconcile_payment

        pending = Payment.objects.filter(
            booking=booking,
            payment_status=Payment.STATUS_PENDING,
        ).select_related('invoice', 'booking').order_by('-created_at').first()

        if pending:
            reconcile_payment(pending)

        booking.refresh_from_db()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        booking = self.get_object()
        # Allow both the booking owner and staff to cancel
        if booking.customer != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # Lock the row to prevent concurrent cancel/approve races.
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status not in ['pending_approval', 'approved', 'awaiting_payment']:
                return Response({'detail': 'This booking cannot be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

            before = {'status': booking.status}
            booking.status = 'cancelled'
            reason = request.data.get('cancellation_reason', '')
            if reason:
                booking.cancellation_reason = reason
            # Release the unit if assigned
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        # Expire any live PayMongo checkout session so the customer cannot
        # complete payment after cancelling.  Best-effort and outside the
        # transaction (it performs network I/O); the webhook's "never
        # resurrect a cancelled booking" guard remains the last resort.
        if before['status'] in ('approved', 'awaiting_payment'):
            from apps.payments.views import expire_pending_payments
            expire_pending_payments(booking)

        # If cancelled by an admin, create an audit log
        if request.user.is_staff and booking.customer != request.user:
            create_audit_log(
                actor=request.user, action='booking_cancelled', booking=booking,
                summary=f'Admin cancelled booking {booking.booking_number}: {reason}' if reason else f'Admin cancelled booking {booking.booking_number}',
                before_state=before, after_state={'status': booking.status},
                request=request,
            )
        else:
            # Customer cancelled their own booking — still log for completeness
            create_audit_log(
                actor=request.user, action='booking_cancelled', booking=booking,
                summary=f'Customer cancelled booking {booking.booking_number}: {reason}' if reason else f'Customer cancelled booking {booking.booking_number}',
                before_state=before, after_state={'status': booking.status},
                request=request,
            )

        notify.notify_booking_cancelled(booking)
        return Response(BookingSerializer(booking).data)

    # ── Admin actions ──

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'pending_approval':
            return Response({'detail': 'Only pending bookings can be approved.'}, status=status.HTTP_400_BAD_REQUEST)

        before = {'status': booking.status}

        with transaction.atomic():
            # Lock the row to prevent concurrent admin actions
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status != 'pending_approval':
                return Response({'detail': 'Only pending bookings can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
            booking.status = 'awaiting_payment'
            booking.save()

        create_audit_log(
            actor=request.user, action='booking_approved', booking=booking,
            summary=f'Approved booking {booking.booking_number}',
            before_state=before, after_state={'status': booking.status},
            request=request,
        )
        notify.notify_booking_approved(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'pending_approval':
            return Response({'detail': 'Only pending bookings can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        ser = BookingStatusUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        before = {'status': booking.status}

        with transaction.atomic():
            # Lock the row to prevent concurrent admin actions
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status != 'pending_approval':
                return Response({'detail': 'Only pending bookings can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)
            booking.status = 'rejected'
            booking.rejection_reason = ser.validated_data.get('rejection_reason', '')
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        create_audit_log(
            actor=request.user, action='booking_rejected', booking=booking,
            summary=f'Rejected booking {booking.booking_number}: {booking.rejection_reason}',
            before_state=before, after_state={'status': booking.status},
            request=request,
        )
        notify.notify_booking_rejected(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Admin manually confirms payment (development simulation).

        In production, payment is confirmed via PayMongo webhook only.
        This endpoint is restricted to superusers and is intended for
        development/testing. It MUST be disabled in production by
        setting ALLOW_MANUAL_PAYMENT_CONFIRM=False in the environment.
        """
        from django.conf import settings as s

        if not getattr(s, 'ALLOW_MANUAL_PAYMENT_CONFIRM', False):
            return Response(
                {'detail': 'Manual payment confirmation is disabled in production.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        booking = self.get_object()
        if not request.user.is_superuser:
            return Response({'detail': 'Not authorized. Only superusers can manually confirm payments.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'awaiting_payment':
            return Response({'detail': 'Booking must be awaiting payment.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.status = 'confirmed'
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'booked'
                booking.vehicle_unit.save()
            booking.save()

            # Keep financial records consistent with the webhook path: mark
            # the invoice paid and record a Payment so the audit trail does
            # not diverge from the normal checkout flow.
            from apps.payments.models import Invoice, Payment
            invoice = Invoice.objects.filter(booking=booking).first()
            if invoice:
                invoice.invoice_status = Invoice.STATUS_PAID
                invoice.save(update_fields=['invoice_status', 'updated_at'])
            pending = Payment.objects.filter(
                booking=booking, payment_status=Payment.STATUS_PENDING,
            ).order_by('-created_at').first()
            if pending:
                pending.mark_paid()

        create_audit_log(
            actor=request.user, action='payment_confirmed', booking=booking,
            summary=f'Manually confirmed payment for booking {booking.booking_number}',
            before_state={'status': 'awaiting_payment'},
            after_state={'status': booking.status},
            request=request,
        )
        logger.info(
            'Payment manually confirmed by admin %s (id=%s) for booking %s',
            request.user.email, request.user.id, booking.booking_number,
        )

        notify.notify_payment_successful(booking)
        notify.notify_booking_confirmed(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-waiting')
    def mark_waiting(self, request, pk=None):
        """Transition confirmed → waiting_for_pickup before handover day."""
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'confirmed':
            return Response(
                {'detail': 'Only confirmed bookings can be marked waiting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Lock the row to prevent concurrent admin actions
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status != 'confirmed':
                return Response(
                    {'detail': 'Only confirmed bookings can be marked waiting.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            before = {'status': booking.status}
            booking.status = 'waiting_for_pickup'
            booking.save()

        create_audit_log(
            actor=request.user, action='booking_marked_waiting', booking=booking,
            summary=f'Marked booking {booking.booking_number} as waiting for pickup',
            before_state=before, after_state={'status': booking.status},
            request=request,
        )
        notify.notify_pickup_reminder(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-active')
    def mark_active(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status not in ['confirmed', 'waiting_for_pickup']:
            return Response({'detail': 'Only confirmed or waiting bookings can be marked active.'}, status=status.HTTP_400_BAD_REQUEST)
        if not booking.vehicle_unit:
            return Response({'detail': 'A vehicle unit must be assigned before activating.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Lock the row to prevent concurrent admin actions
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status not in ['confirmed', 'waiting_for_pickup']:
                return Response({'detail': 'Only confirmed or waiting bookings can be marked active.'}, status=status.HTTP_400_BAD_REQUEST)
            before = {'status': booking.status, 'unit': booking.vehicle_unit.plate_number if booking.vehicle_unit else None}
            booking.status = 'active'
            booking.handover_time = timezone.now()
            booking.vehicle_unit.status = 'active_rental'
            booking.vehicle_unit.save()
            booking.save()

        create_audit_log(
            actor=request.user, action='rental_activated', booking=booking,
            summary=f'Activated rental for booking {booking.booking_number}',
            before_state=before, after_state={'status': booking.status},
            request=request,
        )
        notify.notify_rental_activated(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'active':
            return Response({'detail': 'Only active bookings can be marked complete.'}, status=status.HTTP_400_BAD_REQUEST)

        return_unit_status = request.data.get('return_unit_status', '').strip()
        valid_statuses = ['available', 'maintenance', 'inactive']
        if return_unit_status not in valid_statuses:
            return Response(
                {'detail': f'return_unit_status is required and must be one of: {", ".join(valid_statuses)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Lock the row to prevent concurrent admin actions
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status != 'active':
                return Response({'detail': 'Only active bookings can be marked complete.'}, status=status.HTTP_400_BAD_REQUEST)

            before = {'status': booking.status, 'return_unit_status': None}
            booking.status = 'completed'
            booking.return_unit_status = return_unit_status
            booking.return_time_actual = timezone.now()
            if booking.vehicle_unit:
                booking.vehicle_unit.status = return_unit_status
                booking.vehicle_unit.save()
            booking.save()

        create_audit_log(
            actor=request.user, action='rental_completed', booking=booking,
            summary=f'Completed booking {booking.booking_number} (unit status: {return_unit_status})',
            before_state=before, after_state={'status': booking.status, 'return_unit_status': return_unit_status},
            request=request,
        )
        notify.notify_vehicle_returned(booking)
        notify.notify_transaction_completed(booking)
        return Response(BookingSerializer(booking).data)

    # ── Admin: Vehicle Unit Assignment ──

    @action(detail=True, methods=['post'], url_path='assign-unit')
    def assign_unit(self, request, pk=None):
        """Admin assigns a vehicle unit to a booking (any status after approval)."""
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status not in ['awaiting_payment', 'confirmed', 'waiting_for_pickup']:
            return Response({'detail': 'Booking must be awaiting payment, confirmed, or waiting for pickup.'}, status=status.HTTP_400_BAD_REQUEST)

        unit_id = request.data.get('unit_id')
        reason = request.data.get('reason', 'Initial assignment')
        if not unit_id:
            return Response({'detail': 'unit_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit_id = int(unit_id)
        except (TypeError, ValueError):
            return Response({'detail': 'unit_id must be a valid integer.'}, status=status.HTTP_400_BAD_REQUEST)

        before = {
            'status': booking.status,
            'unit_plate': booking.vehicle_unit.plate_number if booking.vehicle_unit else None,
        }

        # Lock both the booking and the target unit to prevent race conditions
        # between two admins assigning units to the same booking simultaneously.
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            try:
                unit = VehicleUnit.objects.select_for_update().get(pk=unit_id, vehicle=booking.vehicle)
            except VehicleUnit.DoesNotExist:
                return Response({'detail': 'Vehicle unit not found or does not belong to this vehicle model.'}, status=status.HTTP_404_NOT_FOUND)

            if unit.status != 'available':
                return Response({'detail': f'Unit {unit.plate_number} is not available (status: {unit.get_status_display()}).'}, status=status.HTTP_400_BAD_REQUEST)

            previous_unit = booking.vehicle_unit
            previous_plate = previous_unit.plate_number if previous_unit else None

            booking.vehicle_unit = unit
            # Assigning a unit to a confirmed booking reserves it for the
            # customer — the booking advances to waiting_for_pickup.
            if booking.status == 'confirmed':
                booking.status = 'waiting_for_pickup'
            booking.save()

            unit.status = 'booked'
            unit.save()

            if previous_unit and previous_unit != unit:
                previous_unit.status = 'available'
                previous_unit.save()

            AssignmentHistory.objects.create(
                booking=booking,
                previous_unit=previous_unit,
                new_unit=unit,
                reason=reason,
                changed_by=request.user,
            )

            after = {'status': booking.status, 'unit_plate': unit.plate_number}

        action_type = 'unit_changed' if previous_plate else 'unit_assigned'
        create_audit_log(
            actor=request.user, action=action_type, booking=booking,
            summary=f'{"Changed" if previous_plate else "Assigned"} unit for booking {booking.booking_number}: '
                    f'{"None" if not previous_plate else previous_plate} → {unit.plate_number}',
            before_state=before, after_state=after,
            request=request,
        )

        if previous_plate:
            notify.notify_unit_changed(booking, previous_plate, unit.plate_number, reason)
        else:
            notify.notify_unit_assigned(booking, unit)

        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['get'], url_path='assignment-history')
    def assignment_history(self, request, pk=None):
        """Return the assignment history for this booking."""
        booking = self.get_object()
        if booking.customer != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        history = booking.assignment_history.select_related(
            'previous_unit', 'new_unit', 'changed_by',
        ).all()
        return Response(AssignmentHistorySerializer(history, many=True).data)


# ─────────────────────────────────────────────
#  Availability  (VehicleUnit-aware)
# ─────────────────────────────────────────────

class AvailabilityView(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        vehicle_id = request.query_params.get('vehicle_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([vehicle_id, start_date, end_date]):
            return Response(
                {'detail': 'vehicle_id, start_date, and end_date are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if end < start:
            return Response({'available': False, 'reason': 'End date must be after start date.'})
        if start < timezone.now().date():
            return Response({'available': False, 'reason': 'Start date cannot be in the past.'})

        try:
            vehicle_pk = int(vehicle_id)
        except (TypeError, ValueError):
            return Response(
                {'available': False, 'reason': 'Invalid vehicle_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            vehicle = Vehicle.objects.get(pk=vehicle_pk)
        except Vehicle.DoesNotExist:
            return Response({'available': False, 'reason': 'Vehicle not found.'})

        # Count available units (not currently in an occupying status)
        total_units = VehicleUnit.objects.filter(vehicle=vehicle).count()
        if total_units == 0:
            return Response({'available': False, 'reason': 'No units available for this vehicle.'})

        # Units that are already booked for this date range
        booked_unit_ids = Booking.objects.filter(
            vehicle=vehicle,
            vehicle_unit__isnull=False,
            status__in=UNIT_OCCUPYING_STATUSES,
            pickup_date__lt=end,
            return_date__gt=start,
        ).values_list('vehicle_unit_id', flat=True)

        # Also exclude units that are manually reserved/booked/maintenance/etc.
        unavailable_ids = VehicleUnit.objects.filter(
            vehicle=vehicle, status__in=UNIT_UNAVAILABLE_STATUSES,
        ).values_list('id', flat=True)

        blocked_ids = set(booked_unit_ids) | set(unavailable_ids)
        available_count = total_units - VehicleUnit.objects.filter(
            vehicle=vehicle, id__in=blocked_ids,
        ).count()

        available = available_count > 0

        rental_days = max(1, (end - start).days + 1)
        pricing = compute_rental_pricing(vehicle, rental_days)

        return Response({
            'available': available,
            'reason': None if available else 'No units available for the selected dates.',
            'total_units': total_units,
            'available_units': available_count,
            'rental_days': rental_days,
            'price_per_day': str(pricing['price_per_day']),
            'subtotal': str(pricing['subtotal']),
            'discount_percent': str(pricing['discount_percent']),
            'discount_amount': str(pricing['discount_amount']),
            'discount_policy': pricing['discount_policy'],
            'estimated_total': str(pricing['estimated_total']),
        })


# ─────────────────────────────────────────────
#  Dashboard views
# ─────────────────────────────────────────────

class CustomerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        # Use DB-level aggregation for summary counts (O(1) query)
        summary_qs = (
            Booking.objects
            .filter(customer=request.user)
            .values('status')
            .annotate(count=Count('id'))
        )
        summary = {item['status']: item['count'] for item in summary_qs}

        bookings = Booking.objects.filter(
            customer=request.user,
        ).select_related('vehicle').order_by('-created_at')
        serializer = DashboardBookingSerializer(bookings, many=True)

        return Response({
            'summary': summary,
            'total': len(serializer.data),
            'bookings': serializer.data,
        })


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        # Use DB-level aggregation for summary counts (O(1) query)
        summary_qs = (
            Booking.objects
            .values('status')
            .annotate(count=Count('id'))
        )
        summary = {item['status']: item['count'] for item in summary_qs}
        summary['total'] = sum(summary.values())

        bookings = Booking.objects.select_related('customer', 'vehicle').order_by('-created_at')
        serializer = AdminDashboardBookingSerializer(bookings, many=True)

        return Response({
            'summary': summary,
            'total': len(serializer.data),
            'bookings': serializer.data,
        })


# ─────────────────────────────────────────────
#  Identity snapshot image serving
# ─────────────────────────────────────────────

class IdentitySnapshotImageView(APIView):
    """Serve immutable identity-snapshot images through signed URLs.

    The snapshot contains copies of the customer's identity document photos
    captured at booking time.  These copies are separate from the live
    profile documents, so later profile edits never alter a completed
    transaction's record.

    Access is controlled by a short-lived signed token encoding
    "booking_id.user_id.doc_index.side".
    """
    permission_classes = [AllowAny]
    throttle_scope = 'identity_doc_image'
    # Per-user throttle keyed on the signed token's owner (not just the IP),
    # so a single leaked URL cannot be scraped from many machines.
    throttle_classes = [IdentityImageThrottle]

    def get(self, request, pk, doc_index, side):
        from apps.accounts.serializers import unsign_identity_snapshot_image_token

        token = request.query_params.get('token', '')
        if not token:
            if not request.user.is_authenticated:
                raise Http404
            return self._serve_authorized(request.user, pk, doc_index, side)

        try:
            signed_value = unsign_identity_snapshot_image_token(token)
        except (SignatureExpired, BadSignature):
            raise Http404

        parts = signed_value.split('.')
        if len(parts) != 4:
            raise Http404
        token_booking_id, token_user_id, token_doc_index, token_side = parts

        if token_booking_id != str(pk):
            raise Http404
        if token_doc_index != str(doc_index):
            raise Http404
        if token_side != side:
            raise Http404

        # If the request carries a session, double-check ownership.
        if request.user.is_authenticated and request.user.id != int(token_user_id) and not request.user.is_staff:
            raise Http404

        booking = get_object_or_404(Booking, pk=pk)
        if booking.customer_id != int(token_user_id):
            raise Http404

        return self._serve(booking, doc_index, side)

    def _serve_authorized(self, user, pk, doc_index, side):
        """Auth-based access fallback for API clients sending a JWT."""
        booking = get_object_or_404(Booking, pk=pk)
        if booking.customer != user and not user.is_staff:
            raise Http404
        return self._serve(booking, doc_index, side)

    def _serve(self, booking, doc_index, side):
        snapshot = booking.identity_snapshot or {}
        documents = snapshot.get('documents', [])
        try:
            idx = int(doc_index)
        except (ValueError, TypeError):
            raise Http404
        if idx < 0 or idx >= len(documents):
            raise Http404

        doc = documents[idx]
        name = doc.get(f'{side}_image') if side in ('front', 'back') else None
        if not name:
            raise Http404

        try:
            file_handle = private_identity_storage().open(name)
        except (FileNotFoundError, OSError, ValueError):
            raise Http404

        ext = name.lower().rsplit('.', 1)[-1] if '.' in name else 'jpeg'
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
        }
        content_type = mime_map.get(ext, 'image/jpeg')
        return FileResponse(file_handle, content_type=content_type)
