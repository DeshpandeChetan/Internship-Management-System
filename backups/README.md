# Backups

- `legacy_migrations/`: preserved historical migration snapshots, formerly in
  `migration_backups/`. They are not database backups and must not be copied over
  active app migrations or executed against the current database.
- `data/`: generated database and upload backups; excluded from Git.
- `../scripts/backup.py`: creates a timestamped UTC backup directory containing
  `db.sqlite3` and `media.zip`, using Django's configured database and media paths.

From the project root with the virtual environment activated:

```powershell
python scripts/backup.py
```

Pause application writes and uploads while taking a backup so the database and
media archive represent the same state. SQLite uses its native backup API.
The script leaves originals untouched and creates a new directory on every run.
Keep a protected off-machine copy; backups contain personal information.
Secrets and Google credentials are not included: protect those separately.

To restore, stop the application, preserve the current database and media in a
separate location, then restore `db.sqlite3` to the configured database path and
extract `media.zip` into the configured `MEDIA_ROOT`. Use the matching code and
migration version, run `python manage.py check`, and restart. Test restoration in
an isolated copy before replacing live data. Never commit backup contents.
