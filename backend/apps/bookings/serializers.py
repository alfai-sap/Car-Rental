from django.utils import timezone
from rest_framework import serializers
from apps.bookings.models import Booking, AssignmentHistory
from apps.accounts.serializers import make_identity_image_token, make_identity_snapshot_image_token
from apps.core.ids import HashedIdField
from apps.vehicles.models import VehicleUnit, UNIT_UNAVAILABLE_STATUSES

# Statuses that occupy a VehicleUnit
UNIT_OCCUPYING_STATUSES = ['approved', 'awaiting_payment', 'confirmed', 'waiting_for_pickup', 'active']


class BookingSerializer(serializers.ModelSerializer):
    hash_id = HashedIdField('booking', source='id', read_only=True)
    vehicle_hash_id = HashedIdField('vehicle', source='vehicle_id', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    customer_identity_docs = serializers.SerializerMethodField(read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    vehicle_images = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    identity_snapshot = serializers.SerializerMethodField(read_only=True)
    vehicle_unit_plate = serializers.SerializerMethodField(read_only=True)
    vehicle_unit_status = serializers.SerializerMethodField(read_only=True)
    assigned_by = serializers.SerializerMethodField(read_only=True)
    return_unit_status = serializers.CharField(read_only=True)
    return_time_actual = serializers.DateTimeField(read_only=True)
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'hash_id', 'booking_number', 'customer', 'customer_email', 'customer_name',
            'customer_phone', 'customer_identity_docs', 'identity_snapshot',
            'vehicle', 'vehicle_hash_id', 'vehicle_name', 'vehicle_images', 'vehicle_unit',
            'vehicle_unit_plate', 'vehicle_unit_status', 'assigned_by',
            'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'discount_percent', 'discount_amount',
            'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'cancellation_reason',
            'handover_time', 'return_time_actual', 'return_unit_status',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'booking_number', 'customer', 'vehicle_unit',
            'rental_days', 'subtotal', 'discount_percent', 'discount_amount',
            'estimated_total', 'status',
            'rejection_reason', 'cancellation_reason', 'created_at',
            'updated_at', 'handover_time',
        ]

    def get_vehicle_unit_plate(self, obj):
        return obj.vehicle_unit.plate_number if obj.vehicle_unit else None

    def get_vehicle_unit_status(self, obj):
        return obj.vehicle_unit.get_status_display() if obj.vehicle_unit else None

    def get_assigned_by(self, obj):
        """Return the name of the admin who last assigned/changed the unit."""
        last = obj.assignment_history.order_by('-created_at').first()
        if last and last.changed_by:
            return f"{last.changed_by.first_name} {last.changed_by.last_name}"
        return None

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_customer_identity_docs(self, obj):
        docs = obj.customer.identity_documents.all()
        result = []
        for doc in docs:
            front_token = make_identity_image_token(doc.id, doc.user_id, 'front')
            back_token = make_identity_image_token(doc.id, doc.user_id, 'back')
            item = {
                'id': doc.id,
                'document_type': doc.document_type,
                'document_number': doc.document_number,
                'front_image': f'/api/identity-documents/{doc.id}/image/front/?token={front_token}',
                'back_image': f'/api/identity-documents/{doc.id}/image/back/?token={back_token}' if doc.back_image else None,
            }
            result.append(item)
        return result

    def get_identity_snapshot(self, obj):
        """Return the immutable identity snapshot captured at booking time.

        Image URLs point to immutable snapshot copies (not the live profile
        documents), so editing the customer's identity documents later never
        changes a completed transaction's record.
        """
        snapshot = obj.identity_snapshot or {}
        documents = snapshot.get('documents', [])
        enriched = []
        for idx, doc in enumerate(documents):
            front = doc.get('front_image')
            back = doc.get('back_image')
            item = {
                'id': doc.get('id'),
                'document_type': doc.get('document_type'),
                'document_number': doc.get('document_number'),
                'index': doc.get('index', idx),
                'front_image': (
                    f'/api/bookings/{obj.id}/identity-snapshot-image/{idx}/front/?token='
                    f'{make_identity_snapshot_image_token(obj.id, obj.customer_id, idx, "front")}'
                ) if front else None,
                'back_image': (
                    f'/api/bookings/{obj.id}/identity-snapshot-image/{idx}/back/?token='
                    f'{make_identity_snapshot_image_token(obj.id, obj.customer_id, idx, "back")}'
                ) if back else None,
            }
            enriched.append(item)
        snapshot['documents'] = enriched
        return snapshot

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def get_vehicle_images(self, obj):
        images = []
        for img in obj.vehicle.images.all():
            try:
                url = img.image.url
            except (ValueError, OSError):
                continue
            images.append({
                'id': img.id,
                'image': url,
                'is_primary': img.is_primary,
            })
        return images

    def validate(self, data):
        if self.instance is not None:
            # Block modification of core fields on existing bookings
            for blocked in ('vehicle', 'pickup_date', 'return_date', 'pickup_time', 'return_time'):
                if blocked in data:
                    raise serializers.ValidationError({blocked: 'This field cannot be modified after booking.'})
            # For updates, only validate that return_date >= pickup_date if
            # return_date is being explicitly changed (pickup_date is blocked above)
            return_date = data.get('return_date', self.instance.return_date)
            if return_date < self.instance.pickup_date:
                raise serializers.ValidationError({'return_date': 'Return date must be after pickup date.'})
            return data

        customer = self.context['request'].user
        pickup_date = data.get('pickup_date')
        return_date = data.get('return_date')
        vehicle = data.get('vehicle')

        # ── Booking eligibility (email verified + profile + identity) ──
        if not customer.is_verified:
            raise serializers.ValidationError({
                'verified': 'Please verify your email address before booking.',
            })

        if not customer.is_profile_complete():
            raise serializers.ValidationError({
                'profile': 'Please complete your profile information before booking. Go to your profile to add it.',
            })

        if not customer.is_identity_complete():
            raise serializers.ValidationError({
                'identity': 'You must upload a driver\'s license before booking. Go to your profile to add it.',
            })

        if pickup_date and return_date:
            if return_date < pickup_date:
                raise serializers.ValidationError({'return_date': 'Return date must be on or after pickup date.'})
            if pickup_date < timezone.now().date():
                raise serializers.ValidationError({'pickup_date': 'Pickup date cannot be in the past.'})

        if vehicle:
            # ── Vehicle listing status check ──
            if vehicle.status != 'available':
                raise serializers.ValidationError({
                    'vehicle': 'This vehicle is currently unavailable for booking.',
                })

            # VehicleUnit-level availability: at least one unit must be free
            total = VehicleUnit.objects.filter(vehicle=vehicle).count()
            if total == 0:
                raise serializers.ValidationError({
                    'vehicle': 'No units available for this vehicle. Please contact the administrator.',
                })

            booked_unit_ids = Booking.objects.filter(
                vehicle=vehicle,
                vehicle_unit__isnull=False,
                status__in=UNIT_OCCUPYING_STATUSES,
                pickup_date__lt=return_date,
                return_date__gt=pickup_date,
            ).values_list('vehicle_unit_id', flat=True)

            unavailable_ids = VehicleUnit.objects.filter(
                vehicle=vehicle, status__in=UNIT_UNAVAILABLE_STATUSES,
            ).values_list('id', flat=True)

            if unavailable_ids:
                booked_unit_ids = set(booked_unit_ids) | set(unavailable_ids)

            available_count = total - VehicleUnit.objects.filter(
                vehicle=vehicle, id__in=booked_unit_ids,
            ).count()

            if available_count <= 0:
                raise serializers.ValidationError({
                    'vehicle': 'No units available for the selected dates.',
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
    hash_id = HashedIdField('booking', source='id', read_only=True)
    vehicle_hash_id = HashedIdField('vehicle', source='vehicle_id', read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    vehicle_image = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'hash_id', 'booking_number', 'vehicle', 'vehicle_hash_id',
            'vehicle_name', 'vehicle_image',
            'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'cancellation_reason',
            'created_at', 'updated_at',
        ]

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def get_vehicle_image(self, obj):
        primary = obj.vehicle.images.filter(is_primary=True).first()
        if primary and primary.image:
            try:
                return primary.image.url
            except (ValueError, OSError):
                pass
        first = obj.vehicle.images.first()
        if first and first.image:
            try:
                return first.image.url
            except (ValueError, OSError):
                pass
        return None


class AdminDashboardBookingSerializer(serializers.ModelSerializer):
    """Serializer for admin dashboard listing with customer info."""
    hash_id = HashedIdField('booking', source='id', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    vehicle_name = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'hash_id', 'booking_number', 'customer', 'customer_email', 'customer_name',
            'vehicle', 'vehicle_name', 'pickup_date', 'return_date', 'pickup_time', 'return_time',
            'rental_days', 'subtotal', 'estimated_total', 'status', 'status_display',
            'special_request', 'rejection_reason', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"


class AssignmentHistorySerializer(serializers.ModelSerializer):
    previous_plate = serializers.SerializerMethodField(read_only=True)
    new_plate = serializers.SerializerMethodField(read_only=True)
    changed_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AssignmentHistory
        fields = [
            'id', 'booking', 'previous_unit', 'previous_plate',
            'new_unit', 'new_plate', 'reason', 'changed_by',
            'changed_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_previous_plate(self, obj):
        return obj.previous_unit.plate_number if obj.previous_unit else None

    def get_new_plate(self, obj):
        return obj.new_unit.plate_number

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return f"{obj.changed_by.first_name} {obj.changed_by.last_name}"
        return None
