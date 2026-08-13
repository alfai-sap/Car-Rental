from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.bookings import views

router = DefaultRouter()
router.register(r'bookings', views.BookingViewSet, basename='booking')

urlpatterns = [
    path('bookings/availability/', views.AvailabilityView.as_view({'get': 'list'}), name='booking-availability'),
    path('bookings/<int:pk>/identity-snapshot-image/<int:doc_index>/<str:side>/', views.IdentitySnapshotImageView.as_view(), name='booking-identity-snapshot-image'),
    path('dashboard/customer/', views.CustomerDashboardView.as_view(), name='customer-dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('', include(router.urls)),
]
