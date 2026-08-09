from django.urls import path
from apps.accounts import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/token/refresh/', views.CookieTokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/verify-email/', views.VerifyEmailView.as_view(), name='auth-verify-email'),
    path('auth/resend-verification/', views.ResendVerificationView.as_view(), name='auth-resend-verification'),
    path('auth/me/', views.MeView.as_view(), name='auth-me'),
    path('auth/reset-password/', views.PasswordResetRequestView.as_view(), name='auth-reset-request'),
    path('auth/reset-password/confirm/', views.PasswordResetConfirmView.as_view(), name='auth-reset-confirm'),
    path('identity-documents/', views.IdentityDocumentUploadView.as_view(), name='identity-documents'),
    path('identity-documents/<int:pk>/', views.IdentityDocumentDetailView.as_view(), name='identity-document-detail'),
    path('identity-documents/<int:pk>/image/<str:side>/', views.IdentityDocumentImageView.as_view(), name='identity-document-image'),
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
]
