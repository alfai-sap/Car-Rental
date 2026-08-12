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


def _identity_image_token(doc_pk, user_pk):
    """Short-lived signed token for identity document image access (5 min).

    Encodes both the document ID and the user ID so that the image view
    can verify ownership cryptographically — no Authorization header
    needed.  This allows <img> tags to load identity documents securely.

    Format: "doc_pk.user_pk"
    """
    return account_token_generator._email_verifier.signer.sign(f'{doc_pk}.{user_pk}')


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
        base_username = validated_data['email'].split('@')[0]
        username = base_username
        # Avoid UNIQUE constraint collisions when two users share the same
        # email local-part (e.g. john@gmail.com and john@yahoo.com).
        # Retry with incrementing suffixes until we find a free username.
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{suffix}'
            suffix += 1
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
    # ── Document types with human labels and example placeholders ──
    # No format validation is enforced on document_number — the example
    # serves only as a visual guide in the input field placeholder.
    DOCUMENT_TYPE_CONFIG = {
        'drivers_license': {
            'label': "Driver's License",
            'example': 'ABC12-34-567890',
        },
        'passport': {
            'label': 'Passport',
            'example': 'A1234567B',
        },
        'national_id': {
            'label': 'National ID (PhilSys)',
            'example': '1234-5678901-2',
        },
        'sss_id': {
            'label': 'SSS ID',
            'example': '34-1234567-8',
        },
        'umid': {
            'label': 'UMID (Unified Multi-Purpose ID)',
            'example': '0111-1234567-8',
        },
        'prc_id': {
            'label': 'PRC ID',
            'example': '1234567',
        },
        'postal_id': {
            'label': 'Postal ID',
            'example': '123456789012',
        },
    }

    VALID_DOCUMENT_TYPES = list(DOCUMENT_TYPE_CONFIG.keys())

    class Meta:
        model = IdentityDocument
        fields = ['id', 'document_type', 'document_number', 'front_image', 'back_image', 'submitted_at', 'updated_at']
        read_only_fields = ['submitted_at', 'updated_at']

    def validate_document_type(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Document type is required.')
        value = value.strip().lower()
        if value not in self.VALID_DOCUMENT_TYPES:
            raise serializers.ValidationError(
                f'Invalid document type. Allowed: {", ".join(sorted(self.VALID_DOCUMENT_TYPES))}.'
            )
        return value

    def validate_document_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Document number is required.')
        return value.strip()

    def validate(self, data):
        # No format validation on document_number — free-form input
        # with the example serving only as a placeholder guide.
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Build a token that cryptographically binds the document to its owner.
        # The image view will verify ownership from the token alone — no
        # Authorization header required, so <img> tags work in the browser.
        token = _identity_image_token(instance.id, instance.user_id)
        if instance.front_image:
            data['front_image'] = f'/api/identity-documents/{instance.id}/image/front/?token={token}'
        if instance.back_image:
            data['back_image'] = f'/api/identity-documents/{instance.id}/image/back/?token={token}'
        return data


class UserSerializer(serializers.ModelSerializer):
    identity_documents = IdentityDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'is_verified', 'is_staff', 'identity_documents']
