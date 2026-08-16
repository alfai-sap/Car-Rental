"""Rate limiting for signed identity-document image URLs.

Identity-document and snapshot images are served through short-lived signed
URLs so ``<img>`` tags can load them without an Authorization header (the JWT
access token lives in memory, not in a cookie).  A leaked URL is therefore a
bearer token for PII, so we rate-limit by the token's *owner* rather than only
by IP: a single leaked URL cannot be scraped at scale from many machines.
"""
from rest_framework.throttling import ScopedRateThrottle


def _token_user_id(token):
    """Return the owning user id embedded in a signed image token, or None.

    Both token shapes embed the user id as the 2nd dotted field:

      identity images  -> "doc_pk.user_pk.side"
      snapshot images  -> "booking_id.user_id.doc_index.side"
    """
    from apps.accounts.serializers import (
        IMAGE_TOKEN_MAX_AGE,
        unsign_identity_image_token,
        unsign_identity_snapshot_image_token,
    )

    for unsign in (unsign_identity_image_token, unsign_identity_snapshot_image_token):
        try:
            value = unsign(token, max_age=IMAGE_TOKEN_MAX_AGE)
        except Exception:
            continue
        parts = value.split('.')
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    return None


class IdentityImageThrottle(ScopedRateThrottle):
    """Per-user throttle keyed on the authenticated user or the token owner.

    Falls back to the request IP only when neither a session nor a valid token
    is present (e.g. a malformed request), preserving the anti-abuse property
    of the default throttle.
    """

    def get_cache_key(self, request, view):
        ident = None

        if getattr(request, 'user', None) and request.user.is_authenticated:
            ident = f'user-{request.user.pk}'
        else:
            token = request.query_params.get('token', '')
            uid = _token_user_id(token) if token else None
            if uid:
                ident = f'user-{uid}'

        if not ident:
            ident = self.get_ident(request)

        return self.cache_format % {'scope': self.scope, 'ident': ident}
