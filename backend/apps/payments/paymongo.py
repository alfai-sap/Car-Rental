"""
PayMongo API integration — checkout session creation.

This module handles all direct communication with the PayMongo API.
No sensitive payment credentials (card numbers, CVV, GCash PIN) ever
touch this server.  The customer completes payment on PayMongo's
secure hosted page.
"""
import base64
import logging
from typing import Optional, Dict, Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PAYMONGO_API_BASE = 'https://api.paymongo.com/v1'


def _headers() -> Dict[str, str]:
    """Authorization headers for the PayMongo API."""
    secret = settings.PAYMONGO_SECRET_KEY
    if not secret:
        raise PayMongoError('PAYMONGO_SECRET_KEY is not configured.')
    return {
        'Authorization': f'Basic {_encode_basic_auth(secret)}',
        'Content-Type': 'application/json',
    }


def _encode_basic_auth(secret_key: str) -> str:
    """Base64-encode the secret key for HTTP Basic Auth."""
    return base64.b64encode(f'{secret_key}:'.encode()).decode()


class PayMongoError(Exception):
    """Raised when the PayMongo API returns an error."""


def create_checkout_session(
    *,
    amount,
    currency: str = 'PHP',
    description: str,
    payment_reference: str,
    success_url: str,
    cancel_url: str,
    customer_email: Optional[str] = None,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a PayMongo Checkout Session and return its details.

    `amount` may be a Decimal (preferred) or float, expressed in the base
    currency unit (e.g. PHP pesos).  It is converted to integer centavos
    exactly to avoid floating-point rounding errors.

    Returns a dict with:
        checkout_url  — where the customer pays
        session_id    — PayMongo session ID
        paymongo_payment_id — ID for webhook matching
        status        — initial status from PayMongo

    Raises PayMongoError on failure.
    """
    from decimal import Decimal

    url = f'{PAYMONGO_API_BASE}/checkout_sessions'

    # Convert to integer centavos exactly (avoid float rounding errors).
    amount_cents = int(Decimal(str(amount)) * 100)

    line_items = [{
        'amount': amount_cents,  # PayMongo uses centavos
        'currency': currency,
        'description': description[:255],
        'name': description[:100],
        'quantity': 1,
    }]

    payload: Dict[str, Any] = {
        'data': {
            'attributes': {
                'line_items': line_items,
                'payment_method_types': [
                    'card',
                    'gcash',
                    'grab_pay',
                    'paymaya',
                ],
                'send_email_receipt': bool(customer_email),
                'show_description': True,
                'show_line_items': True,
                'description': description[:255],
                'reference_number': payment_reference,
                'success_url': success_url,
                'cancel_url': cancel_url,
            }
        }
    }

    if customer_email:
        payload['data']['attributes']['customer_email'] = customer_email
    if customer_name:
        payload['data']['attributes']['customer_name'] = customer_name
    if customer_phone:
        payload['data']['attributes']['customer_phone'] = customer_phone

    try:
        response = requests.post(
            url,
            json=payload,
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as e:
        logger.error('PayMongo checkout request failed: %s', e)
        raise PayMongoError(f'Failed to connect to PayMongo: {e}')

    try:
        data = response.json()
    except ValueError:
        logger.error('PayMongo checkout returned non-JSON (HTTP %s)', response.status_code)
        raise PayMongoError('PayMongo returned an unexpected response.')

    if response.status_code not in (200, 201):
        error_detail = _extract_error(data)
        logger.error(
            'PayMongo checkout error (HTTP %s): %s',
            response.status_code, error_detail,
        )
        raise PayMongoError(error_detail)

    attrs = data.get('data', {}).get('attributes', {})
    checkout_url = attrs.get('checkout_url', '')
    session_id = data['data']['id']

    payments = attrs.get('payments', [])
    paymongo_payment_id = payments[0]['id'] if payments else ''

    logger.info(
        'PayMongo checkout session created: ref=%s paymongo_id=%s',
        payment_reference, session_id,
    )

    return {
        'checkout_url': checkout_url,
        'session_id': session_id,
        'paymongo_payment_id': paymongo_payment_id,
        'status': attrs.get('status', 'pending'),
    }


def expire_checkout_session(session_id: str) -> bool:
    """Expire a live PayMongo Checkout Session.

    Called when a booking is cancelled while its payment is still pending,
    so the customer can no longer complete the hosted checkout page.

    Returns True on success, False if the request failed (e.g. the session
    was already expired, the gateway is unreachable, or the session id is
    missing).  Failures are logged but never raised — cancelling a booking
    must succeed even if the gateway is down.
    """
    if not session_id:
        return False

    url = f'{PAYMONGO_API_BASE}/checkout_sessions/{session_id}/expire'

    try:
        response = requests.post(url, headers=_headers(), timeout=10)
    except (requests.RequestException, PayMongoError) as e:
        logger.error('PayMongo checkout expiry request failed for %s: %s', session_id, e)
        return False

    if response.status_code not in (200, 201, 204):
        logger.error(
            'PayMongo checkout expiry failed for %s (HTTP %s)',
            session_id, response.status_code,
        )
        return False

    logger.info('PayMongo checkout session expired: session_id=%s', session_id)
    return True


def retrieve_payment(paymongo_payment_id: str) -> Dict[str, Any]:
    """Retrieve a payment by its PayMongo ID.

    Useful for verifying payment status outside of webhooks.
    """
    url = f'{PAYMONGO_API_BASE}/payments/{paymongo_payment_id}'

    try:
        response = requests.get(url, headers=_headers(), timeout=10)
    except requests.RequestException as e:
        logger.error('PayMongo payment retrieval failed: %s', e)
        raise PayMongoError(f'Failed to connect to PayMongo: {e}')

    try:
        data = response.json()
    except ValueError:
        logger.error('PayMongo payment retrieval returned non-JSON (HTTP %s)', response.status_code)
        raise PayMongoError('PayMongo returned an unexpected response.')

    if response.status_code != 200:
        raise PayMongoError(_extract_error(data))

    return data['data']['attributes']


def _extract_error(data: Dict[str, Any]) -> str:
    """Extract a human-readable error message from PayMongo's response."""
    errors = data.get('errors', [])
    if errors:
        detail = errors[0].get('detail', '')
        code = errors[0].get('code', '')
        return f'{detail} (code: {code})' if code else detail
    return 'Unknown PayMongo error.'
