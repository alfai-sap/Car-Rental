"""Private file storage for sensitive uploads.

Identity documents (driver's license / passport photos) and their booking
snapshot copies are stored in a dedicated directory OUTSIDE the public
``MEDIA_ROOT``.  Nothing in this location is ever served by a static file
server — the only way to read these files is through the signed-token views
(``IdentityDocumentImageView`` / ``IdentitySnapshotImageView``).

This is a module-level function (not an instance) so that:

* The storage's ``location`` is resolved lazily from settings (never baked
  into migrations as a machine-specific absolute path).
* Django treats it as a deconstructible ``storage`` callable on ``FileField``.
"""
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def private_identity_storage():
    """Return the private, non-web-served storage for identity documents."""
    return FileSystemStorage(
        location=settings.PRIVATE_MEDIA_ROOT,
        base_url=None,
    )
