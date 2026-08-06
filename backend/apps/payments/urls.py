from django.urls import path

from apps.payments.views import PaymentCreateSessionView, PaymentDetailView, PaymentHistoryView, PaymentWebhookView

urlpatterns = [
    path('payments/create-session/', PaymentCreateSessionView.as_view(), name='payment-create-session'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
]
