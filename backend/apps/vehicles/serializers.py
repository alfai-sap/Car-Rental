from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from apps.vehicles.models import Vehicle, VehicleImage, VehicleUnit


def _validate_upload_image(image):
    """Validate uploaded image at serializer level — size + extension."""
    limit_mb = 10
    if image.size > limit_mb * 1024 * 1024:
        raise serializers.ValidationError(f"Image file too large (max {limit_mb} MB).")
    ext = image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
    if ext not in ('jpg', 'jpeg', 'png', 'webp'):
        raise serializers.ValidationError(
            f"Unsupported file type: .{ext}. Allowed: jpg, jpeg, png, webp."
        )


class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['id', 'image', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            try:
                data['image'] = instance.image.url
            except (ValueError, OSError):
                data['image'] = None
        return data


class VehicleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/catalog view — includes primary image and unit count."""
    primary_image = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()
    available_units = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'primary_image',
            'total_units', 'available_units', 'created_at',
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return self._build_image_url(primary.image)
        first = obj.images.first()
        if first:
            return self._build_image_url(first.image)
        return None

    def _build_image_url(self, field):
        """Return a relative image URL (for proxy compatibility)."""
        try:
            return field.url
        except (ValueError, OSError):
            return None

    def get_total_units(self, obj):
        return obj.units.count()

    def get_available_units(self, obj):
        return obj.units.filter(status='available').count()


class VehicleDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view — includes all images, unit counts (read only)."""
    images = VehicleImageSerializer(many=True, read_only=True)
    total_units = serializers.SerializerMethodField()
    available_units = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'description', 'images',
            'total_units', 'available_units',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'images']

    def get_total_units(self, obj):
        return obj.units.count()

    def get_available_units(self, obj):
        return obj.units.filter(status='available').count()


class VehicleWriteSerializer(serializers.ModelSerializer):
    """Write-only serializer for create/update with image upload support."""

    uploaded_images = serializers.ListField(
        child=serializers.ImageField(validators=[_validate_upload_image]),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Vehicle
        fields = [
            'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'description', 'uploaded_images',
        ]
        extra_kwargs = {
            'make': {'required': True, 'allow_blank': False},
            'model': {'required': True, 'allow_blank': False},
            'year': {'required': True},
            'type': {'required': True, 'allow_blank': False},
            'transmission': {'required': False},
            'fuel': {'required': False},
            'seats': {'required': False},
            'price_per_day': {'required': True},
            'status': {'required': False},
            'description': {'required': False, 'allow_blank': True},
        }

    def validate_make(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Make is required.')
        return value.strip()

    def validate_model(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Model is required.')
        return value.strip()

    def validate_type(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Vehicle type is required.')
        return value.strip()

    def validate_price_per_day(self, value):
        if value is None:
            raise serializers.ValidationError('Price per day is required.')
        if value <= 0:
            raise serializers.ValidationError('Price per day must be greater than 0.')
        return value

    def validate_year(self, value):
        from django.utils import timezone
        current_year = timezone.now().year
        if value < 1900:
            raise serializers.ValidationError('Year must be 1900 or later.')
        if value > current_year + 2:
            raise serializers.ValidationError(f'Year cannot be later than {current_year + 2}.')
        return value

    def create(self, validated_data):
        images = validated_data.pop('uploaded_images', [])
        vehicle = Vehicle.objects.create(**validated_data)
        for img in images:
            VehicleImage.objects.create(vehicle=vehicle, image=img)
        return vehicle

    def update(self, instance, validated_data):
        validated_data.pop('uploaded_images', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class VehicleUnitSerializer(serializers.ModelSerializer):
    vehicle_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VehicleUnit
        fields = [
            'id', 'vehicle', 'vehicle_name', 'plate_number', 'status',
            'mileage', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'vehicle', 'created_at', 'updated_at', 'vehicle_name']

    def get_vehicle_name(self, obj):
        return f"{obj.vehicle.year} {obj.vehicle.make} {obj.vehicle.model}"

    def validate_plate_number(self, value):
        qs = VehicleUnit.objects.filter(plate_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A unit with this plate number already exists.')
        return value
