from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.http import FileResponse, Http404
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

# ── Identity lock constants ──
ACTIVE_BOOKING_STATUSES = [
    'pending_approval', 'approved', 'awaiting_payment',
    'confirmed', 'waiting_for_pickup', 'active',
]
LOCKED_MESSAGE = 'Identity information cannot be modified while you have an active booking.'


def has_active_bookings(user):
    """Return True if the user has any booking that locks identity documents."""
    from apps.bookings.models import Booking
    return Booking.objects.filter(customer=user, status__in=ACTIVE_BOOKING_STATUSES).exists()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def _set_refresh_cookie(response, refresh_token):
    """Set the refresh token as an httpOnly, secure, SameSite cookie."""
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        path='/api/auth/',  # only sent to auth endpoints
    )


def send_verification_email(user):
    token = account_token_generator.make_email_verification_token(user)
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
    """Register a new user account.

    To prevent user-enumeration attacks, duplicate email registrations
    are NOT rejected with an error.  Instead the view returns the same
    success message and sends a verification email only when the
    account does not already exist.

    An attacker cannot determine whether an email is registered by
    observing the API response.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'registration'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            # If the email is already taken, silently pretend success
            # but do NOT create a duplicate account.
            if User.objects.filter(email=email).exists():
                return Response({
                    'detail': 'Account created. Please check your email to verify your account.'
                }, status=status.HTTP_201_CREATED)

            user = serializer.save()
            send_verification_email(user)
            return Response({
                'detail': 'Account created. Please check your email to verify your account.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            if not user.is_verified and not user.is_staff:
                # Return 401 with code=unverified so the frontend can show
                # helpful instructions without leaking to attackers (the
                # HTTP status and generic message remain identical).
                logger.info(
                    'Login attempt for unverified account: %s', email,
                )
                return Response(
                    {'detail': 'Invalid email or password.', 'code': 'email_unverified'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            tokens = get_tokens_for_user(user)
            response = Response({
                'user': UserSerializer(user).data,
                'access': tokens['access'],
            })
            _set_refresh_cookie(response, tokens['refresh'])
            return response
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

        if not account_token_generator.check_email_verification_token(user, data['token']):
            return Response({'detail': 'Verification link has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({'detail': 'Account is already verified.'})

        user.is_verified = True
        user.verified_at = timezone.now()
        user.save()

        # Invalidate all existing sessions — user must sign in fresh after verification
        from rest_framework_simplejwt.token_blacklist.models import (
            OutstandingToken,
        )
        OutstandingToken.objects.filter(user=user).delete()

        return Response({'detail': 'Email verified successfully. You can now sign in.'})


class ResendVerificationView(views.APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'verification_resend'

    def post(self, request):
        email = request.data.get('email', '')
        user = User.objects.filter(email=email, is_verified=False).first()

        if user:
            send_verification_email(user)

        return Response({'detail': 'If an unverified account with that email exists, a new verification link has been sent.'})


class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserSerializer(request.user).data
        data['identity_locked'] = has_active_bookings(request.user)
        return Response(data)

    def put(self, request):
        """Update profile fields (first_name, last_name, phone) and/or password."""
        user = request.user
        updated = False

        # ── Profile fields ──
        for field in ('first_name', 'last_name', 'phone'):
            if field in request.data:
                setattr(user, field, request.data[field])
                updated = True

        if updated:
            user.save(update_fields=[f for f in ('first_name', 'last_name', 'phone') if f in request.data])

        # ── Password change ──
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        new_password2 = request.data.get('new_password2')

        if current_password or new_password or new_password2:
            # All three fields required for password change
            if not current_password:
                return Response({'current_password': 'Current password is required to change password.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if not new_password:
                return Response({'new_password': 'New password is required.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if not new_password2:
                return Response({'new_password2': 'Please confirm your new password.'},
                                status=status.HTTP_400_BAD_REQUEST)

            if not user.check_password(current_password):
                return Response({'current_password': 'Current password is incorrect.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if new_password != new_password2:
                return Response({'new_password2': 'New passwords do not match.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if current_password == new_password:
                return Response({'new_password': 'New password must be different from current password.'},
                                status=status.HTTP_400_BAD_REQUEST)

            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                return Response({'new_password': e.messages}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            # Invalidate all existing sessions
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            OutstandingToken.objects.filter(user=user).delete()

            return Response({'detail': 'Password changed. Please sign in again.'})

        if updated:
            data = UserSerializer(user).data
            data['identity_locked'] = has_active_bookings(user)
            return Response(data)

        return Response({'detail': 'No changes provided.'}, status=status.HTTP_400_BAD_REQUEST)


class IdentityDocumentUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'identity_doc_image'
    parser_classes = [MultiPartParser, FormParser]

    # Prevent disk-abuse by limiting each user to a reasonable number of identity documents
    MAX_IDENTITY_DOCS_PER_USER = 5

    def get(self, request):
        docs = IdentityDocument.objects.filter(user=request.user)
        return Response(IdentityDocumentSerializer(docs, many=True, context={'request': request}).data)

    def post(self, request):
        if has_active_bookings(request.user):
            return Response({'detail': LOCKED_MESSAGE}, status=status.HTTP_403_FORBIDDEN)

        current_count = IdentityDocument.objects.filter(user=request.user).count()
        if current_count >= self.MAX_IDENTITY_DOCS_PER_USER:
            return Response(
                {'detail': f'You can upload up to {self.MAX_IDENTITY_DOCS_PER_USER} identity documents. Please delete an existing one first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        if has_active_bookings(request.user):
            return Response({'detail': LOCKED_MESSAGE}, status=status.HTTP_403_FORBIDDEN)
        doc = get_object_or_404(IdentityDocument, pk=pk, user=request.user)
        serializer = IdentityDocumentSerializer(doc, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if has_active_bookings(request.user):
            return Response({'detail': LOCKED_MESSAGE}, status=status.HTTP_403_FORBIDDEN)
        doc = get_object_or_404(IdentityDocument, pk=pk, user=request.user)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'password_reset'

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
                f"This link will expire in 15 minutes.\n\n"
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

        # Invalidate all existing sessions for this user by blacklisting
        # every outstanding refresh token. This ensures that if someone
        # else had access to a session, they are kicked out.
        from rest_framework_simplejwt.token_blacklist.models import (
            OutstandingToken,
        )
        OutstandingToken.objects.filter(user=user).delete()

        return Response({'detail': 'Password reset successful. Please sign in again.'})


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token', '') or request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # token may already be invalid — that's fine

        response = Response({'detail': 'Logged out successfully.'})
        response.delete_cookie('refresh_token', path='/api/auth/')
        return response


class CookieTokenRefreshView(views.APIView):
    """Refresh the access token using the httpOnly refresh cookie.

    The refresh token is read exclusively from the 'refresh_token'
    httpOnly cookie — never from the request body.  This prevents
    CSRF-based token theft: even if a malicious site sends a POST,
    the browser won't attach the httpOnly cookie unless SameSite
    allows it (and we use SameSite=Lax, which blocks cross-site POST).

    A new access token is returned in the response body.  The
    refresh cookie is rotated (blacklisted + replaced) on each call.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token', '')

        if not refresh_token:
            return Response(
                {'detail': 'No refresh token provided.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.check_exp()
        except Exception:
            return Response(
                {'detail': 'Refresh token is invalid or expired.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Blacklist the old token and rotate
        try:
            token.blacklist()
        except Exception:
            pass

        # Issue new tokens
        user = User.objects.get(pk=token['user_id'])
        new_tokens = get_tokens_for_user(user)

        response = Response({'access': new_tokens['access']})
        _set_refresh_cookie(response, new_tokens['refresh'])
        return response


class NotificationsView(views.APIView):
    """Return real in-app notifications for the current user.

    Supports ?limit=N and ?offset=M query params for pagination.
    Default limit is 50, max 100.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.core.models import Notification

        try:
            limit = int(request.query_params.get('limit', 50))
        except (ValueError, TypeError):
            limit = 50
        limit = max(1, min(limit, 100))

        try:
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0
        offset = max(0, offset)

        qs = Notification.objects.filter(user=request.user).order_by('-created_at')
        unread_count = qs.filter(is_read=False).count()

        notifications_qs = qs[offset:offset + limit]

        data = []
        for n in notifications_qs:
            data.append({
                'id': n.id,
                'notification_type': n.notification_type,
                'type_display': n.get_notification_type_display(),
                'title': n.title,
                'message': n.message,
                'booking_id': n.booking_id,
                'booking_number': n.booking.booking_number if n.booking else None,
                'is_read': n.is_read,
                'link': n.link,
                'created_at': n.created_at,
            })

        return Response({
            'count': qs.count(),
            'unread_count': unread_count,
            'notifications': data,
        })

    def post(self, request):
        """Mark notification(s) as read."""
        from apps.core.models import Notification

        notification_id = request.data.get('notification_id')
        mark_all = request.data.get('mark_all', False)

        qs = Notification.objects.filter(user=request.user)
        if mark_all:
            qs.filter(is_read=False).update(is_read=True)
        elif notification_id:
            qs.filter(pk=notification_id).update(is_read=True)
        else:
            return Response({'detail': 'Provide notification_id or mark_all=true.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Notifications updated.'})


class IdentityDocumentImageView(views.APIView):
    """Serve identity document images through a signed URL.

    Identity documents contain PII and must never be served publicly.
    The URL includes a short-lived signed token (5 min) so that
    <img> tags can load images without Authorization headers.
    The token is scoped to the document id + side, and checked
    against the requesting user's identity.

    Rate-limited to 30 req/min per IP to mitigate scraping within
    the 5-minute token window.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'identity_doc_image'

    def get(self, request, pk, side):
        token = request.query_params.get('token', '')
        if not token:
            # Fall back to auth-based access for non-browser clients
            if not request.user.is_authenticated:
                raise Http404
            return self._serve_image(request.user, pk, side)

        try:
            signed_pk = account_token_generator._email_verifier.signer.unsign(token, max_age=300)
        except (SignatureExpired, BadSignature):
            raise Http404

        if signed_pk != str(pk):
            raise Http404

        # Token valid — verify ownership before serving
        doc = get_object_or_404(IdentityDocument, pk=pk)
        # Require authentication for the token-based path too —
        # signed URLs can leak via browser history, proxy logs, or
        # referrer headers.  The token limits the window, but we must
        # also verify the requesting user owns the document.
        if not request.user.is_authenticated:
            raise Http404
        if doc.user != request.user and not request.user.is_staff:
            raise Http404
        return self._serve_file(doc, side)

    def _serve_image(self, user, pk, side):
        """Auth-based access (for API clients sending JWT)."""
        doc = get_object_or_404(IdentityDocument, pk=pk)
        if doc.user != user and not user.is_staff:
            raise Http404
        return self._serve_file(doc, side)

    def _serve_file(self, doc, side):
        if side == 'front':
            image_field = doc.front_image
        elif side == 'back':
            image_field = doc.back_image
        else:
            return Response({'detail': 'Invalid side.'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_field:
            raise Http404

        try:
            file_handle = image_field.open()
        except (FileNotFoundError, OSError, ValueError):
            raise Http404

        # Determine content type from extension instead of hardcoding jpeg
        ext = image_field.name.lower().rsplit('.', 1)[-1] if '.' in image_field.name else 'jpeg'
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
        }
        content_type = mime_map.get(ext, 'image/jpeg')

        return FileResponse(file_handle, content_type=content_type)
