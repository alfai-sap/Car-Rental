# Deferred discount-policy FK.
#
# Vehicle.discount_policy references core.RentalDiscountPolicy, which cannot
# be created in the same migration as Vehicle because core depends on
# bookings which depends on vehicles (a schema cycle).  This migration adds
# the FK once core's models exist.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('vehicles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='discount_policy',
            field=models.ForeignKey(blank=True, help_text='Optional discount policy override for this vehicle. Leave blank to use the global default policy.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vehicles', to='core.rentaldiscountpolicy'),
        ),
    ]
