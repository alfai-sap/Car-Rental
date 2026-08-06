from rest_framework import serializers
from apps.vehicles.models import Vehicle, VehicleImage


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
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleWriteSerializer(serializers.ModelSerializer):
    """Write-only serializer for create/update — excludes nested images."""
    class Meta:
        model = Vehicle
        fields = [
            'make', 'model', 'year', 'type', 'transmission', 'fuel',
            'seats', 'price_per_day', 'status', 'description',
        ]
