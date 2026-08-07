from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer, BookingStatusUpdateSerializer, DashboardBookingSerializer, AdminDashboardBookingSerializer
from apps.vehicles.models import Vehicle


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related('customer', 'vehicle').prefetch_related('vehicle__images')
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['vehicle', 'status']
    ordering_fields = ['created_at', 'pickup_date']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset() if hasattr(super(), 'get_queryset') else Booking.objects.select_related('customer', 'vehicle').prefetch_related('vehicle__images')
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(customer=user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

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
        booking.status = 'cancelled'
        reason = request.data.get('cancellation_reason', '')
        if reason:
            booking.rejection_reason = reason
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
        booking.status = 'approved'
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'pending_approval':
            return Response({'detail': 'Only pending bookings can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BookingStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'rejected'
        booking.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'awaiting_payment':
            return Response({'detail': 'Booking must be awaiting payment.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = 'confirmed'
        booking.vehicle.status = 'rented'
        booking.vehicle.save()
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-active')
    def mark_active(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status not in ['confirmed', 'waiting_for_pickup']:
            return Response({'detail': 'Only confirmed or waiting bookings can be marked active.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = 'active'
        booking.handover_time = timezone.now()
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        booking = self.get_object()
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        if booking.status != 'active':
            return Response({'detail': 'Only active bookings can be marked complete.'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = 'completed'
        booking.vehicle.status = 'available'
        booking.vehicle.save()
        booking.save()
        return Response(BookingSerializer(booking).data)


class AvailabilityView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        vehicle_id = request.query_params.get('vehicle_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([vehicle_id, start_date, end_date]):
            return Response({'detail': 'vehicle_id, start_date, and end_date are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            start = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if end < start:
            return Response({'available': False, 'reason': 'End date must be after start date.'})

        if start < timezone.now().date():
            return Response({'available': False, 'reason': 'Start date cannot be in the past.'})

        # Check vehicle exists and is available
        try:
            vehicle = Vehicle.objects.get(pk=vehicle_id)
        except Vehicle.DoesNotExist:
            return Response({'available': False, 'reason': 'Vehicle not found.'})

        if vehicle.status not in ['available', 'rented']:
            return Response({'available': False, 'reason': 'Vehicle is not available for booking.'})

        # Only approved or later bookings reserve the vehicle for a date range.
        overlapping = Booking.objects.filter(
            vehicle_id=vehicle_id,
            status__in=['approved', 'awaiting_payment', 'confirmed', 'active'],
            pickup_date__lt=end,
            return_date__gt=start,
        ).exists()

        if overlapping:
            return Response({'available': False, 'reason': 'This vehicle is already booked for the selected dates.'})

        # Calculate pricing — inclusive (Aug 1–2 = 2 days)
        rental_days = max(1, (end - start).days + 1)
        subtotal = vehicle.price_per_day * rental_days

        return Response({
            'available': True,
            'rental_days': rental_days,
            'price_per_day': str(vehicle.price_per_day),
            'subtotal': str(subtotal),
            'estimated_total': str(subtotal),
        })


# ── Dashboard views ──

class CustomerDashboardView(APIView):
    """Returns the authenticated customer's bookings grouped by status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(customer=request.user).select_related('vehicle')
        serializer = DashboardBookingSerializer(bookings, many=True)

        pending = [b for b in serializer.data if b['status'] == 'pending_approval']
        approved = [b for b in serializer.data if b['status'] == 'approved']
        awaiting_payment = [b for b in serializer.data if b['status'] == 'awaiting_payment']
        confirmed = [b for b in serializer.data if b['status'] == 'confirmed']
        active = [b for b in serializer.data if b['status'] == 'active']
        completed = [b for b in serializer.data if b['status'] == 'completed']
        cancelled = [b for b in serializer.data if b['status'] == 'cancelled']
        rejected = [b for b in serializer.data if b['status'] == 'rejected']

        return Response({
            'summary': {
                'total': len(serializer.data),
                'pending_approval': len(pending),
                'approved': len(approved),
                'awaiting_payment': len(awaiting_payment),
                'confirmed': len(confirmed),
                'active': len(active),
                'completed': len(completed),
                'cancelled': len(cancelled),
                'rejected': len(rejected),
            },
            'bookings': serializer.data,
        })


class AdminDashboardView(APIView):
    """Returns all bookings for admin review, grouped by status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        bookings = Booking.objects.select_related('customer', 'vehicle').all()
        serializer = AdminDashboardBookingSerializer(bookings, many=True)

        pending = [b for b in serializer.data if b['status'] == 'pending_approval']
        approved = [b for b in serializer.data if b['status'] == 'approved']
        awaiting_payment = [b for b in serializer.data if b['status'] == 'awaiting_payment']
        confirmed = [b for b in serializer.data if b['status'] == 'confirmed']
        active = [b for b in serializer.data if b['status'] == 'active']
        completed = [b for b in serializer.data if b['status'] == 'completed']
        cancelled = [b for b in serializer.data if b['status'] == 'cancelled']
        rejected = [b for b in serializer.data if b['status'] == 'rejected']

        return Response({
            'summary': {
                'total': len(serializer.data),
                'pending_approval': len(pending),
                'approved': len(approved),
                'awaiting_payment': len(awaiting_payment),
                'confirmed': len(confirmed),
                'active': len(active),
                'completed': len(completed),
                'cancelled': len(cancelled),
                'rejected': len(rejected),
            },
            'bookings': serializer.data,
        })
