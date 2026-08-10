from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated, SAFE_METHODS
from django_filters.rest_framework import DjangoFilterBackend

from apps.vehicles.models import Vehicle, VehicleImage, VehicleUnit
from apps.vehicles.serializers import (
    VehicleListSerializer,
    VehicleDetailSerializer,
    VehicleWriteSerializer,
    VehicleImageSerializer,
    VehicleUnitSerializer,
)


class IsAdminOrReadOnly(IsAdminUser):
    """Allow read-only access to anyone, write access to admins only."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.prefetch_related('images').filter(status='available')
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'transmission', 'fuel', 'seats', 'status']
    search_fields = ['make', 'model', 'description']
    ordering_fields = ['price_per_day', 'year', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return VehicleListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return VehicleWriteSerializer
        return VehicleDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Guests see only available vehicles; admins see all statuses
        if self.request.user.is_staff:
            return Vehicle.objects.prefetch_related('images').all()
        return qs


class VehicleImageViewSet(viewsets.ModelViewSet):
    queryset = VehicleImage.objects.all()
    serializer_class = VehicleImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        return VehicleImage.objects.filter(vehicle_id=self.kwargs.get('vehicle_pk'))

    def perform_create(self, serializer):
        serializer.save(vehicle_id=self.kwargs['vehicle_pk'])


class VehicleUnitViewSet(viewsets.ModelViewSet):
    queryset = VehicleUnit.objects.select_related('vehicle').all()
    serializer_class = VehicleUnitSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]  # authenticated only; write is admin
    lookup_field = 'pk'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return VehicleUnit.objects.select_related('vehicle').filter(
            vehicle_id=self.kwargs.get('vehicle_pk')
        )

    def perform_create(self, serializer):
        serializer.save(vehicle_id=self.kwargs['vehicle_pk'])
