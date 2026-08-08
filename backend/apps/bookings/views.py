import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.bookings.models import Booking, AssignmentHistory
from apps.bookings.serializers import (
    BookingSerializer, BookingStatusUpdateSerializer,
    DashboardBookingSerializer, AdminDashboardBookingSerializer,
    AssignmentHistorySerializer, UnitAssignmentSerializer,
)
from apps.core import services as notify
from apps.vehicles.models import Vehicle, VehicleUnit

logger = logging.getLogger(__name__)


# ── Booking-reserving statuses ──
# Only these statuses occupy a VehicleUnit and block availability.
UNIT_OCCUPYING_STATUSES = ['approved', 'awaiting_payment', 'confirmed', 'waiting_for_pickup', 'active']



def _build_identity_snapshot(user):
    """Capture current identity documents as an immutable JSON snapshot."""
    docs = user.identity_documents.all()
    return {
        'customer_name': f"{user.first_name} {user.last_name}",
        'customer_email': user.email,
        'customer_phone': user.phone,
        'documents': [
            {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_number': doc.document_number,
            }
            for doc in docs
        ],
        'captured_at': timezone.now().isoformat(),
    }


def _find_available_unit(vehicle, pickup_date, return_date):
    """Find an available VehicleUnit for the given vehicle and date range."""
    booked_unit_ids = Booking.objects.filter(
        vehicle=vehicle,
        vehicle_unit__isnull=False,
        status__in=UNIT_OCCUPYING_STATUSES,
        pickup_date__lt=return_date,
        return_date__gt=pickup_date,
    ).values_list('vehicle_unit_id', flat=True)

    return VehicleUnit.objects.filter(
        vehicle=vehicle,
        status='available',
    ).exclude(id__in=booked_unit_ids).first()


# ─────────────────────────────────────────────
#  Booking ViewSet
# ─────────────────────────────────────────────

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related(
        'customer', 'vehicle', 'vehicle_unit',
    ).prefetch_related('vehicle__images')
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

    # ── Customer actions ──

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.customer != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status not in ['pending_approval', 'approved', 'awaiting_payment']:
            return Response({'detail': 'This booking cannot be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.status = 'cancelled'
            reason = request.data.get('cancellation_reason', '')
            if reason:
                booking.cancellation_reason = reason
            # Release the unit if assigned
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        return Response(BookingSerializer(booking).data)

    # ── Admin actions ──

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'pending_approval':
            return Response({'detail': 'Only pending bookings can be approved.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.status = 'awaiting_payment'
            # Unit assignment is manual — admin assigns via assign-unit endpoint
            booking.save()

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

        with transaction.atomic():
            booking.status = 'rejected'
            booking.rejection_reason = ser.validated_data.get('rejection_reason', '')
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        notify.notify_booking_rejected(booking)
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Admin manually confirms payment (development simulation).

        In production, payment is confirmed via PayMongo webhook only.
        This endpoint is a backdoor for testing the full booking workflow
        before payment integration is activated.
        """
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'awaiting_payment':
            return Response({'detail': 'Booking must be awaiting payment.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.status = 'confirmed'
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'booked'
                booking.vehicle_unit.save()
            booking.save()

        # Audit log
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
        booking.status = 'waiting_for_pickup'
        booking.save()
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
            booking.status = 'active'
            booking.handover_time = timezone.now()
            booking.vehicle_unit.status = 'active_rental'
            booking.vehicle_unit.save()
            booking.save()

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
            booking.status = 'completed'
            booking.return_unit_status = return_unit_status
            booking.return_time_actual = timezone.now()
            if booking.vehicle_unit:
                booking.vehicle_unit.status = return_unit_status
                booking.vehicle_unit.save()
            booking.save()

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
            unit = VehicleUnit.objects.get(pk=unit_id, vehicle=booking.vehicle)
        except VehicleUnit.DoesNotExist:
            return Response({'detail': 'Vehicle unit not found or does not belong to this vehicle model.'}, status=status.HTTP_404_NOT_FOUND)

        if unit.status != 'available':
            return Response({'detail': f'Unit {unit.plate_number} is not available (status: {unit.get_status_display()}).'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            previous_unit = booking.vehicle_unit
            previous_plate = previous_unit.plate_number if previous_unit else None

            booking.vehicle_unit = unit
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
    permission_classes = [IsAuthenticated]

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
            vehicle = Vehicle.objects.get(pk=vehicle_id)
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

        # Also exclude units that are in maintenance or inactive
        unavailable_statuses = ['maintenance', 'inactive']
        unavailable_ids = VehicleUnit.objects.filter(
            vehicle=vehicle, status__in=unavailable_statuses,
        ).values_list('id', flat=True)

        blocked_ids = set(booked_unit_ids) | set(unavailable_ids)
        available_count = total_units - VehicleUnit.objects.filter(
            vehicle=vehicle, id__in=blocked_ids,
        ).count()

        available = available_count > 0

        rental_days = max(1, (end - start).days + 1)
        subtotal = vehicle.price_per_day * rental_days

        return Response({
            'available': available,
            'reason': None if available else 'No units available for the selected dates.',
            'total_units': total_units,
            'available_units': available_count,
            'rental_days': rental_days,
            'price_per_day': str(vehicle.price_per_day),
            'subtotal': str(subtotal),
            'estimated_total': str(subtotal),
        })


# ─────────────────────────────────────────────
#  Dashboard views
# ─────────────────────────────────────────────

class CustomerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(
            customer=request.user,
        ).select_related('vehicle')
        serializer = DashboardBookingSerializer(bookings, many=True)

        groups = {}
        for key in ['pending_approval', 'approved', 'awaiting_payment', 'confirmed',
                     'waiting_for_pickup', 'active', 'completed', 'cancelled', 'rejected']:
            groups[key] = [b for b in serializer.data if b['status'] == key]

        return Response({
            'summary': {key: len(v) for key, v in groups.items()},
            'total': len(serializer.data),
            'bookings': serializer.data,
        })


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        bookings = Booking.objects.select_related('customer', 'vehicle').all()
        serializer = AdminDashboardBookingSerializer(bookings, many=True)

        groups = {}
        for key in ['pending_approval', 'approved', 'awaiting_payment', 'confirmed',
                     'waiting_for_pickup', 'active', 'completed', 'cancelled', 'rejected']:
            groups[key] = [b for b in serializer.data if b['status'] == key]

        return Response({
            'summary': {key: len(v) for key, v in groups.items()},
            'total': len(serializer.data),
            'bookings': serializer.data,
        })
