"""
JWT authentication with session-version revocation.

Extends SimpleJWT's JWTAuthentication so that bumping a user's
`token_version` field immediately invalidates every access token issued
before the bump — regardless of the token's remaining lifetime.

Combined with SimpleJWT's built-in `CHECK_REVOKE_TOKEN` (which binds tokens
to the user's password hash), this gives real-time logout on password change,
email verification, and sign-out across all devices.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class JWTAuthenticationWithTokenVersion(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        # Legacy tokens minted before token_version was introduced carry no
        # claim; accept them (they are still protected by the password-hash
        # revocation check and their expiry).
        claim_version = validated_token.get('token_version')
        if claim_version is not None and claim_version != user.token_version:
            raise AuthenticationFailed(
                'This session has been revoked. Please sign in again.',
                code='token_revoked',
            )

        return user
