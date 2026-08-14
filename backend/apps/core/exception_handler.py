"""
Custom DRF exception handler — ensures all error responses
(including 500, 403, 404) return JSON instead of HTML.
"""
import math

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import Throttled
from rest_framework import status


def format_throttle_message(wait_seconds):
    """Return the uniform rate-limit message shown for all throttled paths.

    Used both by DRF's ScopedRateThrottle (via this exception handler) and by
    account-level login lockout so that both brute-force paths present the
    identical, non-enumerating response.
    """
    seconds = max(1, int(math.ceil(float(wait_seconds))))
    plural = 's' if seconds != 1 else ''
    return f'Please try again after {seconds} second{plural}.'


def custom_exception_handler(exc, context):
    """Return DRF errors as JSON, and catch any unhandled exception
    so we never leak an HTML error page to the API consumer."""
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Normalize throttling responses so every rate-limited endpoint
        # returns the same concise message.
        if isinstance(exc, Throttled):
            wait = getattr(exc, 'wait', None)
            if wait is not None:
                response.data = {'detail': format_throttle_message(wait)}
        return response

    # Unhandled exception (e.g. a 500 server error) —
    # return a consistent JSON error
    return Response(
        {
            'detail': 'An unexpected server error occurred.',
            'code': 'server_error',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
