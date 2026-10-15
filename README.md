# Internship Management and Assessment System

Django IMS manages student internships, mentor assignments, assessments, breaks,
and internship completion progress through role-specific dashboards.

## Features

- Google OAuth login, existing-account linking, activation and approval checks.
- Admin, HoD/coordinator, faculty mentor, evaluator, and student roles.
- Student, programme, batch, department, and organisation management.
- Internship records, documents, verification, and completion tracking.
- Mentor assignments, configurable assessments, marks, and consolidated scores.
- Break records, internship overlaps, notifications, audit logs, and report exports.

## Technologies

Python, Django, SQLite, django-allauth, Bootstrap 5. Templates use Bootstrap,
jQuery, DataTables, Chart.js, and Select2, including CDN-hosted assets.

## Installation

Use Python 3.12 or newer for Django 6.x. Run from the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install pandas openpyxl reportlab requests cryptography
```

The additional packages above are runtime dependencies used by reports and OAuth
that are not all explicitly listed in the existing requirements file. For Unix
shells, activate with `source venv/bin/activate`.

## Configuration

Configuration lives in `ims/settings.py`. The current project does not load a
`.env` file automatically; creating one alone will not change settings.

- SQLite database: `db.sqlite3` at the project root.
- Uploads: `media/`, served at `/media/` during development.
- Django Sites: `SITE_ID = 1`.
- Authentication adapters: `apps.authentication.adapter`.

Before deployment, configure a private `SECRET_KEY`, set `DEBUG = False`, restrict
`ALLOWED_HOSTS`, and configure HTTPS, static/media serving, and email as needed.
Keep credentials and uploaded user content out of Git. The existing
`client_secret.json` and `.env` ignore rules remain in place.

### Google OAuth

Create a Google OAuth web client and register this development redirect URI:
`http://127.0.0.1:8000/accounts/google/login/callback/`.
Use the exact host and scheme used to open the application.

After migrations, sign into Django admin at `/admin/`, configure Site 1 for your
host, and create a Social Application for Google with the client ID and secret.

## Database and Running

For a new installation:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Authorized users are routed to their role dashboard.
For an existing installation, back up the database and media before migrating.
Keep the checked-in migrations; do not regenerate or delete them during setup.

## Verification

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Existing checks may warn about a missing `static/` directory and deprecated
allauth settings. These are existing configuration issues.

## Backups

```powershell
python scripts/backup.py
```

See [backup procedures](backups/README.md) for consistency requirements, contents,
storage, and restoration. Generated backups go into ignored `backups/data/`.
Historical migration snapshots are kept separately in `backups/legacy_migrations/`.

## Structure

```text
apps/authentication/     OAuth, account authorization, roles and permissions
apps/core/               IMS models, forms, workflows, reports and dashboards
ims/                     Django settings and root URLs
templates/               Shared and role-specific templates
scripts/                 Maintenance scripts
backups/                 Backup documentation and historical migration snapshots
media/                   Local uploaded files (ignored)
manage.py                Django command entry point
requirements.txt         Existing dependency list
```
