from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('admin/audit-logs/', views.AuditLogListView.as_view(), name='admin-audit-logs'),
    path('admin/discount-policy/', views.RentalDiscountPolicyView.as_view(), name='admin-discount-policy'),
    path('discount-policy/', views.PublicDiscountPolicyView.as_view(), name='discount-policy'),
]
