"""
Security headers middleware — adds CSP, Permissions-Policy, and other
hardening headers to every response.
"""
from django.conf import settings


class SecurityHeadersMiddleware:
    """Add security headers to all HTTP responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy — defence against XSS, data injection
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-src https://paymongo.com https://pm.paymongo.com; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'"
        )
        response['Content-Security-Policy'] = csp

        # Permission Policy — restrict browser features
        response['Permissions-Policy'] = (
            'camera=(), '
            'microphone=(), '
            'geolocation=(), '
            'payment=()'
        )

        # Cross-Origin isolation headers (already handled by django-cors-headers,
        # but extra hardening never hurts)
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'

        # Cache control for sensitive pages (override if views set their own)
        if not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'no-store, max-age=0'

        return response
