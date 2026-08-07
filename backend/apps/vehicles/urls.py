from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from apps.vehicles import views

router = DefaultRouter()
router.register(r'vehicles', views.VehicleViewSet, basename='vehicle')

# Nested router for vehicle images: /api/vehicles/{vehicle_pk}/images/
vehicle_router = NestedDefaultRouter(router, r'vehicles', lookup='vehicle')
vehicle_router.register(r'images', views.VehicleImageViewSet, basename='vehicle-images')
vehicle_router.register(r'units', views.VehicleUnitViewSet, basename='vehicle-units')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(vehicle_router.urls)),
]
