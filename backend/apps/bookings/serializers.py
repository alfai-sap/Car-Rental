from django.utils import timezone
from rest_framework import serializers
from apps.bookings.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'customer', 'customer_email', 'customer_name',
            'vehicle', 'vehicle_name', 'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'booking_number', 'customer', 'rental_days', 'subtotal',
            'estimated_total', 'status', 'rejection_reason', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def validate(self, data):
        if self.instance is None:  # create only
            pickup_date = data.get('pickup_date')
            return_date = data.get('return_date')

            if pickup_date and return_date:
                if return_date < pickup_date:
                    raise serializers.ValidationError({'return_date': 'Return date must be after pickup date.'})

                if pickup_date < timezone.now().date():
                    raise serializers.ValidationError({'pickup_date': 'Pickup date cannot be in the past.'})

                # Prevent same user from having multiple active requests for the same vehicle.
                # Different users can submit overlapping booking requests (they are not yet approved).
                request = self.context.get('request')
                user = request.user if request and request.user.is_authenticated else None
                vehicle = data.get('vehicle')
                if user and vehicle:
                    own_existing = Booking.objects.filter(
                        vehicle=vehicle,
                        customer=user,
                        status__in=['pending_approval', 'approved', 'awaiting_payment', 'confirmed', 'active'],
                    )
                    if self.instance:
                        own_existing = own_existing.exclude(pk=self.instance.pk)
                    if own_existing.exists():
                        raise serializers.ValidationError({
                            'vehicle': 'You already have a booking request for this vehicle. You can edit your existing booking instead.'
                        })

        return data


class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    """Admin-only: approve or reject a booking."""

    rejection_reason = serializers.CharField(required=True, min_length=1)

    class Meta:
        model = Booking
        fields = ['status', 'rejection_reason']


class DashboardBookingSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer dashboard listing."""
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    vehicle_image = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'vehicle', 'vehicle_name', 'vehicle_image',
            'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'created_at', 'updated_at',
        ]

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def get_vehicle_image(self, obj):
        primary = obj.vehicle.images.filter(is_primary=True).first()
        if primary and hasattr(primary, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        first = obj.vehicle.images.first()
        if first and hasattr(first, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first.image.url)
            return first.image.url
        return None


class AdminDashboardBookingSerializer(serializers.ModelSerializer):
    """Serializer for admin dashboard listing with customer info."""
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'customer', 'customer_email', 'customer_name',
            'vehicle', 'vehicle_name', 'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"
