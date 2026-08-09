from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework import serializers
from apps.accounts.models import User, IdentityDocument


class EmailVerificationTokenGenerator:
    """Stateless token generator for email verification only.

    Uses Django's TimestampSigner so that verification tokens survive
    password changes.  Tokens expire after PASSWORD_RESET_TIMEOUT
    (default 5 min).
    """
    def __init__(self):
        self.signer = TimestampSigner()

    def make_token(self, user):
        return self.signer.sign(str(user.pk))

    def check_token(self, user, token):
        try:
            signed_pk = self.signer.unsign(token, max_age=_get_token_timeout())
            return signed_pk == str(user.pk)
        except (SignatureExpired, BadSignature):
            return False


class AccountTokenGenerator(PasswordResetTokenGenerator):
    """Password-reset token generator that incorporates the user's password hash.

    Uses Django's built-in PasswordResetTokenGenerator so that a reset
    token automatically becomes invalid after the user changes their
    password — preventing token-replay attacks.

    Also provides a short-lived TimestampSigner for email verification,
    where password-change invalidation is NOT desired.
    """
    def __init__(self):
        super().__init__()
        self._email_verifier = EmailVerificationTokenGenerator()

    def make_email_verification_token(self, user):
        """Short-lived token for email verification (survives password changes)."""
        return self._email_verifier.make_token(user)

    def check_email_verification_token(self, user, token):
        """Validate an email-verification token."""
        return self._email_verifier.check_token(user, token)


def _get_token_timeout():
    from django.conf import settings
    return getattr(settings, 'PASSWORD_RESET_TIMEOUT', 300)


account_token_generator = AccountTokenGenerator()


def _identity_image_token(pk):
    """Short-lived signed token for identity document image access (5 min).

    Allows <img> tags to load identity documents without Auth headers.
    """
    return account_token_generator._email_verifier.signer.sign(str(pk))


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password', 'password2']
        extra_kwargs = {
            'email': {'validators': []},  # Remove UniqueValidator for anti-enumeration
        }

    def validate_email(self, value):
        # NOTE: We intentionally do NOT reject duplicate emails here.
        # The view handles existing-account silently to prevent
        # user-enumeration attacks (see RegisterView docstring).
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        username = validated_data['email'].split('@')[0]
        user = User.objects.create_user(username=username, is_active=True, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})

        # Decode the uid to get the user
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': 'Invalid reset link.'})

        # Validate the token against the user
        if not account_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({'token': 'Reset link has expired or is invalid.'})

        data['user'] = user
        return data


class IdentityDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityDocument
        fields = ['id', 'document_type', 'document_number', 'front_image', 'back_image', 'submitted_at', 'updated_at']
        read_only_fields = ['submitted_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.front_image:
            token = _identity_image_token(instance.id)
            data['front_image'] = f'/api/identity-documents/{instance.id}/image/front/?token={token}'
        if instance.back_image:
            token = _identity_image_token(instance.id)
            data['back_image'] = f'/api/identity-documents/{instance.id}/image/back/?token={token}'
        return data


class UserSerializer(serializers.ModelSerializer):
    identity_documents = IdentityDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_verified', 'is_staff', 'identity_documents']
