import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.bookings.models import Booking
from apps.bookings.serializers import (
    BookingSerializer, BookingStatusUpdateSerializer,
    DashboardBookingSerializer, AdminDashboardBookingSerializer,
)
from apps.vehicles.models import Vehicle, VehicleUnit

logger = logging.getLogger(__name__)


# ── Booking-reserving statuses ──
# Only these statuses occupy a VehicleUnit and block availability.
UNIT_OCCUPYING_STATUSES = ['approved', 'awaiting_payment', 'confirmed', 'waiting_for_pickup', 'active']

# ── Shared email helper ──
def _send_booking_email(booking, subject, template_name, extra_context=None):
    """Send a booking-related email to the customer."""
    user = booking.customer
    ctx = {
        'first_name': user.first_name or 'there',
        'booking': booking,
        'booking_number': booking.booking_number,
        'vehicle_name': f"{booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}",
        'pickup_date': booking.pickup_date,
        'return_date': booking.return_date,
        'estimated_total': booking.estimated_total,
    }
    if extra_context:
        ctx.update(extra_context)

    text_content = (
        f"Hi {ctx['first_name']},\n\n"
        f"{subject}\n\n"
        f"Booking: {ctx['booking_number']}\n"
        f"Vehicle: {ctx['vehicle_name']}\n"
        f"Dates: {ctx['pickup_date']} – {ctx['return_date']}\n"
        f"Total: ₱{ctx['estimated_total']}\n\n"
        f"View your booking: {settings.FRONTEND_URL}/transactions/{booking.id}\n\n"
        f"– Car Rental Team"
    )

    try:
        html_content = render_to_string(template_name, ctx)
    except Exception:
        html_content = None

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    if html_content:
        msg.attach_alternative(html_content, 'text/html')
    try:
        msg.send()
    except Exception as e:
        logger.error(f"Failed to send booking email to {user.email}: {e}")


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
            vehicle = serializer.validated_data['vehicle']
            pickup = serializer.validated_data['pickup_date']
            ret = serializer.validated_data['return_date']

            unit = _find_available_unit(vehicle, pickup, ret)
            snapshot = _build_identity_snapshot(self.request.user)

            booking = serializer.save(
                customer=self.request.user,
                vehicle_unit=unit,
                identity_snapshot=snapshot,
            )

        _send_booking_email(
            booking,
            'Booking Request Received',
            'emails/booking_submitted.html',
            extra_context={'booking': booking},
        )

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

            # Reserve the assigned unit (or assign one if not already)
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'reserved'
                booking.vehicle_unit.save()
            else:
                unit = _find_available_unit(booking.vehicle, booking.pickup_date, booking.return_date)
                if unit:
                    unit.status = 'reserved'
                    unit.save()
                    booking.vehicle_unit = unit

            booking.save()

        _send_booking_email(
            booking,
            'Booking Approved — Payment Required',
            'emails/booking_approved.html',
            extra_context={'booking': booking},
        )

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
            # Release unit
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        _send_booking_email(
            booking,
            'Booking Request Declined',
            'emails/booking_rejected.html',
            extra_context={'rejection_reason': booking.rejection_reason},
        )

        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
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

        _send_booking_email(
            booking,
            'Payment Confirmed — Booking Finalized',
            'emails/booking_confirmed.html',
        )

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

        with transaction.atomic():
            booking.status = 'active'
            booking.handover_time = timezone.now()
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'active_rental'
                booking.vehicle_unit.save()
            booking.save()

        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'active':
            return Response({'detail': 'Only active bookings can be marked complete.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            booking.status = 'completed'
            if booking.vehicle_unit:
                booking.vehicle_unit.status = 'available'
                booking.vehicle_unit.save()
            booking.save()

        return Response(BookingSerializer(booking).data)


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
