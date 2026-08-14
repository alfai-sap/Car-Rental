"""
Opaque, signed identifiers for public URLs.

Raw primary keys are sequential and guessable, letting anyone enumerate
records by editing the number in a URL (``/transactions/1``, ``/vehicles/2``,
…).  Instead of exposing PKs, we sign them with Django's ``django.core.signing``
(which HMACs the payload with SECRET_KEY) so that:

* The value in the URL is opaque and unguessable.
* The value is tamper-evident — forging ``/transactions/<other id>`` is
  impossible without the secret key.
* Decoding is cheap and stateless (no DB round-trip for a lookup table).

Backwards compatibility: pure-digit values are treated as legacy numeric PKs.
This keeps existing integrations (tests, email links, bookmarks) working while
new URLs use the opaque form.
"""
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers

_SALT = 'car-rental-id'


class InvalidId(Exception):
    """Raised when a value cannot be decoded for the expected model."""


def encode_id(model_name: str, pk) -> str:
    """Return an opaque, signed token for ``model_name`` + ``pk``."""
    return signing.dumps(
        {'m': model_name, 'p': int(pk)},
        salt=_SALT,
        compress=True,
    )


def decode_id(model_name: str, value) -> int:
    """Decode a signed token (or legacy numeric PK) back to an integer PK.

    Raises InvalidId when the value is malformed, expired of trust, or was
    signed for a different model.
    """
    if value is None:
        raise InvalidId('Missing identifier.')

    raw = str(value).strip()

    # Legacy numeric passthrough (backwards compatibility).
    if raw.isdigit():
        return int(raw)

    try:
        data = signing.loads(raw, salt=_SALT)
    except signing.BadSignature as exc:
        raise InvalidId('Invalid identifier.') from exc

    if not isinstance(data, dict) or data.get('m') != model_name:
        raise InvalidId('Identifier does not match the expected resource.')
    try:
        return int(data['p'])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidId('Malformed identifier.') from exc


class HashedIdField(serializers.Field):
    """DRF serializer field that emits an opaque signed ID for a PK.

    Example::

        hash_id = HashedIdField('booking', source='id')
    """

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        kwargs.setdefault('read_only', True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        return encode_id(self.model_name, value)


def resolve_pk_or_404(model_name: str, value):
    """Decode a URL identifier to a PK, or raise Http404 when invalid."""
    try:
        return decode_id(model_name, value)
    except InvalidId as exc:
        raise Http404 from exc


class HashedIdLookupMixin:
    """DRF view mixin that resolves a signed opaque id in place of a raw PK.

    Set ``hashed_id_model_name`` on the view (e.g. 'booking', 'vehicle').
    The view's standard lookup URL kwarg is decoded via :func:`decode_id`,
    which also accepts legacy numeric PKs for backwards compatibility.
    """
    hashed_id_model_name = None

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            raise AssertionError(
                'Expected view %s to be called with a URL keyword argument '
                'named "%s".' % (self.__class__.__name__, lookup_url_kwarg)
            )

        value = self.kwargs[lookup_url_kwarg]
        pk = resolve_pk_or_404(self.hashed_id_model_name, value)

        obj = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj
