from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny, IsAdminUser, SAFE_METHODS
from rest_framework.response import Response
from django.db.models.deletion import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.ids import HashedIdLookupMixin
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


class VehicleViewSet(HashedIdLookupMixin, viewsets.ModelViewSet):
    hashed_id_model_name = 'vehicle'
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

    def destroy(self, request, *args, **kwargs):
        """Block deletion of vehicles referenced by bookings (DB PROTECT)."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {'detail': 'This vehicle cannot be deleted because it is referenced by one or more bookings.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleImageViewSet(viewsets.ModelViewSet):
    queryset = VehicleImage.objects.all()
    serializer_class = VehicleImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def _vehicle_pk(self):
        from apps.core.ids import resolve_pk_or_404

        return resolve_pk_or_404('vehicle', self.kwargs.get('vehicle_pk'))

    def get_queryset(self):
        return VehicleImage.objects.filter(vehicle_id=self._vehicle_pk())

    def perform_create(self, serializer):
        serializer.save(vehicle_id=self._vehicle_pk())


class VehicleUnitViewSet(viewsets.ModelViewSet):
    queryset = VehicleUnit.objects.select_related('vehicle').all()
    serializer_class = VehicleUnitSerializer
    # Fleet units (plate numbers, mileage, notes) are internal operational
    # data.  Restrict all access — read and write — to staff only.
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def _vehicle_pk(self):
        from apps.core.ids import resolve_pk_or_404

        return resolve_pk_or_404('vehicle', self.kwargs.get('vehicle_pk'))

    def get_queryset(self):
        return VehicleUnit.objects.select_related('vehicle').filter(
            vehicle_id=self._vehicle_pk()
        )

    def perform_create(self, serializer):
        serializer.save(vehicle_id=self._vehicle_pk())

    def destroy(self, request, *args, **kwargs):
        """Block deletion of units referenced by bookings/assignment history (DB PROTECT)."""
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {'detail': 'This unit cannot be deleted because it is assigned to one or more bookings.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
