"""Back up the configured SQLite database and media without modifying originals."""

import os
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ims.settings')
    import django
    django.setup()
    from django.conf import settings

    database = settings.DATABASES['default']
    if database['ENGINE'] != 'django.db.backends.sqlite3':
        raise SystemExit('This script supports SQLite only; use your database native backup tool.')
    source = Path(database['NAME']).resolve()
    if not source.is_file():
        raise SystemExit(f'Database not found: {source}')
    target = root / 'backups' / 'data' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target.mkdir(parents=True, exist_ok=False)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(target / 'db.sqlite3') as backup:
            original.backup(backup)
    media = Path(settings.MEDIA_ROOT).resolve()
    with ZipFile(target / 'media.zip', 'w', ZIP_DEFLATED) as archive:
        if media.is_dir():
            for path in media.rglob('*'):
                if path.is_file() and not path.is_symlink():
                    archive.write(path, path.relative_to(media))
    print(f'Backup created: {target}')


if __name__ == '__main__':
    main()
