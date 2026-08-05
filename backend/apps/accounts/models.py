from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for the Car Rental system.

    Extends Django's AbstractUser to allow future customization
    such as phone number, driver's license, and profile picture.
    """

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.get_full_name() or self.username
