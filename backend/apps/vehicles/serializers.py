from rest_framework import serializers
from apps.vehicles.models import Vehicle, VehicleImage, VehicleUnit


class VehicleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleImage
        fields = ['id', 'image', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class VehicleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/catalog view — includes primary image only."""
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'primary_image', 'created_at',
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return self.context.get('request').build_absolute_uri(primary.image.url) if self.context.get('request') else primary.image.url
        first = obj.images.first()
        if first:
            return self.context.get('request').build_absolute_uri(first.image.url) if self.context.get('request') else first.image.url
        return None


class VehicleDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view — includes all images (read only)."""
    images = VehicleImageSerializer(many=True, read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'description', 'images',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'images']


class VehicleWriteSerializer(serializers.ModelSerializer):
    """Write-only serializer for create/update with image upload support."""

    make = serializers.CharField(required=False, allow_blank=True)
    model = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField(required=False, allow_blank=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
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
            'transmission': {'required': False},
            'fuel': {'required': False},
            'price_per_day': {'required': False},
            'description': {'required': False},
        }

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
