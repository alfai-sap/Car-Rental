"""
Signal handlers for the vehicles app.

Post-delete: removes vehicle image files from disk when a database
record is deleted, preventing orphaned files in storage.
"""
import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.vehicles.models import VehicleImage

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=VehicleImage)
def delete_vehicle_image_file(sender, instance, **kwargs):
    """Remove the image file from disk when a VehicleImage record is deleted."""
    if instance.image and instance.image.name:
        try:
            if instance.image.storage.exists(instance.image.name):
                instance.image.storage.delete(instance.image.name)
                logger.info(
                    'Deleted image for VehicleImage id=%s vehicle_id=%s: %s',
                    instance.id, instance.vehicle_id, instance.image.name,
                )
        except Exception as e:
            logger.error(
                'Failed to delete image for VehicleImage id=%s: %s',
                instance.id, e,
            )
