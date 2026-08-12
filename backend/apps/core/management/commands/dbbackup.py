"""
Database backup management command.

Creates a compressed SQL dump of the database using pg_dump.
Stores backups in BACKUP_DIR (configurable via envvar DB_BACKUP_DIR).

Usage:
    python manage.py dbbackup              # Create a timestamped backup
    python manage.py dbbackup --list       # List existing backups
    python manage.py dbbackup --clean 7    # Remove backups older than 7 days
"""
import gzip
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a compressed database backup via pg_dump.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List existing backup files.',
        )
        parser.add_argument(
            '--clean',
            type=int,
            metavar='DAYS',
            help='Remove backup files older than DAYS days.',
        )

    def handle(self, *args, **options):
        backup_dir = Path(os.getenv('DB_BACKUP_DIR', settings.BASE_DIR / 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)

        if options['list']:
            self._list_backups(backup_dir)
            return

        if options['clean']:
            self._clean_backups(backup_dir, options['clean'])
            return

        self._create_backup(backup_dir)

    def _get_db_config(self):
        """Extract database connection info from Django settings."""
        db = settings.DATABASES['default']
        return {
            'NAME': db['NAME'],
            'USER': db['USER'],
            'PASSWORD': db['PASSWORD'],
            'HOST': db.get('HOST', 'localhost'),
            'PORT': str(db.get('PORT', '5432')),
        }

    def _create_backup(self, backup_dir):
        db = self._get_db_config()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{db["NAME"]}_{timestamp}.sql.gz'
        filepath = backup_dir / filename

        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        self.stdout.write(f'Creating backup: {filepath}...')

        try:
            with gzip.open(filepath, 'wb') as f:
                proc = subprocess.run(
                    [
                        'pg_dump',
                        '--host', db['HOST'],
                        '--port', db['PORT'],
                        '--username', db['USER'],
                        '--no-password',
                        '--no-owner',
                        '--format=p',
                        db['NAME'],
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=True,
                )
                f.write(proc.stdout)
        except subprocess.CalledProcessError as e:
            # Clean up partial file on failure
            if filepath.exists():
                filepath.unlink()
            raise CommandError(
                f'pg_dump failed: {e.stderr.decode().strip() if e.stderr else e}'
            )
        except FileNotFoundError:
            raise CommandError(
                'pg_dump not found. Please install the PostgreSQL client tools.\n'
                '  Ubuntu/Debian: apt install postgresql-client\n'
                '  macOS:         brew install libpq && echo \'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"\' >> ~/.zshrc\n'
                '  Windows:       Add the PostgreSQL bin directory to your PATH.'
            )

        size_mb = filepath.stat().st_size / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f'Backup created: {filename} ({size_mb:.1f} MB)'
            )
        )

    def _list_backups(self, backup_dir):
        files = sorted(backup_dir.glob('*.sql.gz'), key=os.path.getmtime, reverse=True)
        if not files:
            self.stdout.write('No backups found.')
            return

        self.stdout.write(f'Backups in {backup_dir}:')
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            self.stdout.write(f'  {f.name}  ({size_mb:.1f} MB)  {mtime.strftime("%Y-%m-%d %H:%M")}')

    def _clean_backups(self, backup_dir, days):
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        for f in backup_dir.glob('*.sql.gz'):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                self.stdout.write(f'Removed: {f.name}')
                removed += 1

        if removed == 0:
            self.stdout.write(f'No backups older than {days} days found.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Removed {removed} backup(s) older than {days} days.')
            )
