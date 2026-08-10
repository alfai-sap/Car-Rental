from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('admin/audit-logs/', views.AuditLogListView.as_view(), name='admin-audit-logs'),
]
