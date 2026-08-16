# Consolidated initial migration for the accounts app.
#
# This single migration creates the User and IdentityDocument models in
# their FINAL state, replacing the previous incremental chain of migrations
# (0001 through 0013).  Migrating from scratch applies only this file —
# no intermediate add/remove/alter steps are replayed.
import apps.accounts.models
import apps.core.storage
import apps.core.validators
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(blank=True, max_length=20, validators=[django.core.validators.RegexValidator(message='Enter a valid 11-digit mobile number (e.g. 09123456789).', regex='^09\\d{9}$')])),
                ('is_verified', models.BooleanField(default=False)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('auth_method', models.CharField(choices=[('email', 'Email'), ('google', 'Google')], default='email', help_text='How this account authenticates (email/password or Google).', max_length=10)),
                ('token_version', models.PositiveIntegerField(default=0, help_text='Increment to revoke all previously issued access tokens.')),
                ('failed_login_attempts', models.PositiveSmallIntegerField(default=0, help_text='Consecutive failed login attempts. Reset on successful login.')),
                ('locked_until', models.DateTimeField(blank=True, help_text='Account is locked until this time. Null when not locked.', null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', apps.accounts.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='IdentityDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(max_length=50)),
                ('document_number', models.CharField(max_length=50)),
                ('front_image', models.ImageField(storage=apps.core.storage.private_identity_storage, upload_to='identity_docs/front/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), apps.core.validators.validate_image_size, apps.core.validators.validate_image_content])),
                ('back_image', models.ImageField(blank=True, null=True, storage=apps.core.storage.private_identity_storage, upload_to='identity_docs/back/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), apps.core.validators.validate_image_size, apps.core.validators.validate_image_content])),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='identity_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
    ]
