"""
Custom DRF exception handler — ensures all error responses
(including 500, 403, 404) return JSON instead of HTML.
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Return DRF errors as JSON, and catch any unhandled exception
    so we never leak an HTML error page to the API consumer."""
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF already handled it — make sure it stays JSON
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
