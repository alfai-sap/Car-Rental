from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
import logging
from rest_framework import status, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, IdentityDocument
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    IdentityDocumentSerializer,
    VerifyEmailSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    account_token_generator,
)

logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def send_verification_email(user):
    token = account_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verify_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"

    first_name = user.first_name or 'there'

    html_content = render_to_string('emails/verify_email.html', {
        'first_name': first_name,
        'verify_url': verify_url,
    })
    text_content = (
        f"Hi {first_name},\n\n"
        f"Thank you for creating a Car Rental account. Please verify your email "
        f"address by clicking the link below:\n\n{verify_url}\n\n"
        f"If you did not create this account, please ignore this email.\n\n"
        f"- Car Rental Team"
    )

    msg = EmailMultiAlternatives(
        subject='Verify your Car Rental account',
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, 'text/html')
    try:
        msg.send()
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")


class RegisterView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            send_verification_email(user)
            return Response({
                'detail': 'Account created. Please check your email to verify your account.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            tokens = get_tokens_for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                **tokens,
            })
        return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)


class VerifyEmailView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not account_token_generator.check_token(user, data['token']):
            return Response({'detail': 'Verification link has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({'detail': 'Account is already verified.'})

        user.is_verified = True
        user.verified_at = timezone.now()
        user.save()
        return Response({'detail': 'Email verified successfully. You can now sign in.'})

        if user.is_verified:
            return Response({'detail': 'Account is already verified.'})

        user.is_verified = True
        user.verified_at = timezone.now()
        user.save()
        return Response({'detail': 'Email verified successfully. You can now sign in.'})


class ResendVerificationView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '')
        user = User.objects.filter(email=email, is_verified=False).first()

        if user:
            send_verification_email(user)

        return Response({'detail': 'If an unverified account with that email exists, a new verification link has been sent.'})


class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class IdentityDocumentUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        docs = IdentityDocument.objects.filter(user=request.user)
        return Response(IdentityDocumentSerializer(docs, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = IdentityDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IdentityDocumentDetailView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        doc = get_object_or_404(IdentityDocument, pk=pk, user=request.user)
        return Response(IdentityDocumentSerializer(doc, context={'request': request}).data)

    def put(self, request, pk):
        doc = get_object_or_404(IdentityDocument, pk=pk, user=request.user)
        serializer = IdentityDocumentSerializer(doc, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        doc = get_object_or_404(IdentityDocument, pk=pk, user=request.user)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()

        if user:
            token = account_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            first_name = user.first_name or 'there'

            html_content = render_to_string('emails/password_reset.html', {
                'first_name': first_name,
                'reset_url': reset_url,
            })
            text_content = (
                f"Hi {first_name},\n\n"
                f"We received a request to reset your password for your Car Rental account.\n\n"
                f"Copy and paste the link below into your browser to reset it:\n"
                f"{reset_url}\n\n"
                f"This link will expire in 5 minutes.\n\n"
                f"If you did not request a password reset, please ignore this email.\n\n"
                f"– Car Rental Team"
            )

            msg = EmailMultiAlternatives(
                subject='Reset your Car Rental password',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, 'text/html')
            try:
                msg.send()
            except Exception as e:
                logger.error(f"Failed to send password reset email to {user.email}: {e}")

        return Response({'detail': 'If the email exists, a reset link has been sent.'})


class PasswordResetConfirmView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = data['user']
        user.set_password(data['password'])
        user.save()
        return Response({'detail': 'Password reset successful.'})


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({'detail': 'Logged out successfully.'})
