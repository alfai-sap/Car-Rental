"""
Signal handlers for the accounts app.

Post-delete: removes identity document image files from disk when
a database record is deleted, preventing orphaned PII files.
"""
import os
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.accounts.models import IdentityDocument

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=IdentityDocument)
def delete_identity_document_files(sender, instance, **kwargs):
    """Remove front/back image files from disk when an IdentityDocument is deleted."""
    for side in ('front_image', 'back_image'):
        file_field = getattr(instance, side, None)
        if file_field and file_field.name:
            try:
                if file_field.storage.exists(file_field.name):
                    file_field.storage.delete(file_field.name)
                    logger.info(
                        'Deleted %s for IdentityDocument id=%s user=%s: %s',
                        side, instance.id, instance.user_id, file_field.name,
                    )
            except Exception as e:
                logger.error(
                    'Failed to delete %s for IdentityDocument id=%s: %s',
                    side, instance.id, e,
                )
