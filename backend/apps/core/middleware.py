"""
Security headers middleware — adds CSP, Permissions-Policy, and other
hardening headers to every response.

All header values are resolved at call time (not at startup), so
changing settings (e.g. via env vars in production) takes effect
without a server restart.
"""
from django.conf import settings


class SecurityHeadersMiddleware:
    """Add security headers to all HTTP responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # ── Content Security Policy ──
        # In DEBUG mode we relax script-src for HMR (Vite dev server).
        # In production we lock down to 'self' only.
        if settings.DEBUG:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' ws://localhost:* http://localhost:* https://accounts.google.com; "
                "frame-src https://paymongo.com https://pm.paymongo.com https://accounts.google.com; "
                "form-action 'self'; "
                "base-uri 'self'; "
                "object-src 'none'"
            )
        else:
            csp = (
                "default-src 'self'; "
                "script-src 'self' https://accounts.google.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://accounts.google.com; "
                "frame-src https://*.paymongo.com https://paymongo.com https://pm.paymongo.com; "
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

        # ── Additional production-only headers ──
        if not settings.DEBUG:
            # Tell browsers to always check for certificate revocation
            response['Expect-CT'] = 'max-age=86400, enforce'
            # DNS prefetch control
            response['X-DNS-Prefetch-Control'] = 'off'

        # Cache control for API responses only — prevents caching of sensitive data
        # while allowing browsers to cache static assets normally.
        if request.path.startswith('/api/') and not response.has_header('Cache-Control'):
            response['Cache-Control'] = 'no-store, max-age=0'

        return response
