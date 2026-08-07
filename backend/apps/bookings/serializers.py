from django.utils import timezone
from rest_framework import serializers
from apps.bookings.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_identity_docs = serializers.SerializerMethodField(read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    vehicle_images = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_number', 'customer', 'customer_email', 'customer_name',
            'customer_phone', 'customer_identity_docs',
            'vehicle', 'vehicle_name', 'vehicle_images',
            'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'handover_time',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'booking_number', 'customer', 'rental_days', 'subtotal',
            'estimated_total', 'status', 'rejection_reason', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_customer_identity_docs(self, obj):
        docs = obj.customer.identity_documents.all()
        request = self.context.get('request')
        result = []
        for doc in docs:
            item = {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_number': doc.document_number,
                'front_image': request.build_absolute_uri(doc.front_image.url) if request and doc.front_image else None,
                'back_image': request.build_absolute_uri(doc.back_image.url) if request and doc.back_image else None,
            }
            result.append(item)
        return result

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def get_vehicle_images(self, obj):
        request = self.context.get('request')
        images = []
        for img in obj.vehicle.images.all():
            images.append({
                'id': img.id,
                'image': request.build_absolute_uri(img.image.url) if request else img.image.url,
                'is_primary': img.is_primary,
            })
        return images

    def validate(self, data):
        if self.instance is None:  # create only
            pickup_date = data.get('pickup_date')
            return_date = data.get('return_date')

            if pickup_date and return_date:
                if return_date < pickup_date:
                    raise serializers.ValidationError({'return_date': 'Return date must be after pickup date.'})

                if pickup_date < timezone.now().date():
                    raise serializers.ValidationError({'pickup_date': 'Pickup date cannot be in the past.'})

                vehicle = data.get('vehicle')
                if vehicle:
                    overlapping = Booking.objects.filter(
                        vehicle=vehicle,
                        status__in=['approved', 'awaiting_payment', 'confirmed', 'active'],
                        pickup_date__lt=return_date,
                        return_date__gt=pickup_date,
                    )
                    if overlapping.exists():
                        raise serializers.ValidationError({
                            'vehicle': 'This vehicle is already booked for the selected dates.'
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
