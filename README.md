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

## Prerequisites

- Python 3.12 or newer with `pip` and `venv` for the project's Django 6.x setup.
  Django and allauth are unpinned in `requirements.txt`, so a fresh installation
  may select different versions from an existing environment.
- Git, a terminal, and a browser.
- Internet access for package installation, Google login, and CDN-hosted UI assets.
- A Google account and access to a Google Cloud project for OAuth credentials.
- SQLite support in Python; no separate database server is required.

Check your tools before starting:

```text
git --version
python --version
python -m pip --version
```

On systems where Python is named `python3`, use `python3` until the virtual
environment is activated. On Windows, `py -3.12` can select an installed Python
3.12 interpreter instead of `python`.

## Clone the Repository

```text
git clone https://github.com/DeshpandeChetan/Internship-Management-System.git
cd Internship-Management-System
```

All commands below run from this directory, which contains `manage.py`,
`requirements.txt`, `ims/`, `apps/`, and `templates/`.

## Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv venv
venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Activate the environment in each new terminal before running project commands.
Use `deactivate` to leave it.

## Install Dependencies

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pandas openpyxl reportlab requests cryptography
python -m pip check
```

The additional packages above are runtime dependencies used by reports and OAuth
that are not all explicitly listed in the existing requirements file. Installing
only `requirements.txt` may therefore leave imports missing. These instructions
do not change the repository's dependency file.

## Configuration

Configuration lives in `ims/settings.py`. The current project does not load a
`.env` file automatically; creating one alone will not change settings.

No environment variables need to be set for the default local setup.
`manage.py`, `ims/asgi.py`, and `ims/wsgi.py` default `DJANGO_SETTINGS_MODULE` to
`ims.settings`. If your shell already sets this variable to another project,
unset it or set it to `ims.settings` before running commands. `SECRET_KEY`,
`DEBUG`, database settings, and Google credentials are not read from environment
variables by this configuration.

- SQLite database: `db.sqlite3` at the project root.
- Uploads: `media/`, served at `/media/` during development.
- Django Sites: `SITE_ID = 1`.
- Authentication adapters: `apps.authentication.adapter`.
- Development defaults: `DEBUG = True` and `ALLOWED_HOSTS = ['*']`.
- Static source directory: `static/`; collected output: `staticfiles/`.

The database, uploaded content, and local credentials are not supplied by cloning.
New installations start with an empty database. Existing installations should
retain their own database and media files.

Before deployment, configure a private `SECRET_KEY`, set `DEBUG = False`, restrict
`ALLOWED_HOSTS`, and configure HTTPS, static/media serving, and email as needed.
Keep credentials and uploaded user content out of Git. The existing
`client_secret.json` and `.env` ignore rules remain in place.

## Initialize the Database

For a fresh installation with the virtual environment active:

```text
After migrations, sign into Django admin at `/admin/`, configure Site 1 for your
host, and create a Social Application for Google with the client ID and secret.

## Database and Running

For a new installation:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py check
```

Supply a username, email address, and password when prompted. Use the Google
account email you intend to use for the IMS admin login. The project's user signal
creates an active, approved admin profile for a newly created superuser.

For an existing installation, back up the database and media before migrating.
Use the checked-in migrations; do not delete them or run `makemigrations` as a
substitute for `migrate` during installation.

## Run the Development Server

```text
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for IMS and `http://127.0.0.1:8000/admin/` for
Django administration. Stop the server with Ctrl+C. Django admin accepts the
superuser username/password, allowing Google configuration before OAuth works.
The development server is for local use.

If port 8000 is occupied, run `python manage.py runserver 8001` and use
`http://127.0.0.1:8001/`; update Google callback and Site settings accordingly.

## Configure Google OAuth Login

1. In a Google Cloud project, configure the OAuth consent screen/audience and
   create an OAuth client of type **Web application**. If the app is in testing
   mode, add the Google accounts used for testing where required by its audience.
2. Register the exact authorized redirect URI:
   `http://127.0.0.1:8000/accounts/google/login/callback/`.
   If configuring a JavaScript origin, use `http://127.0.0.1:8000` without a path.
3. Start Django and sign into `/admin/` with the superuser credentials.
4. Under **Sites**, edit the site whose ID is `1`, matching `SITE_ID = 1`.
   Set its domain to `127.0.0.1:8000` (no scheme or path) and a suitable display name.
5. Under **Social applications**, add one Google application. Enter the Google
   client ID and secret and associate it with Site 1. Leave the optional key blank.
   Avoid multiple Google applications associated with the same site.
6. Sign out of Django admin, open `http://127.0.0.1:8000/`, and choose Google login.
   Use the same email as your admin-created account to link to its assigned role.

Use the same host, port, and scheme throughout: `localhost` and `127.0.0.1` are
different callback hosts. Register a matching callback if you change them. Google
client secrets belong in the configured allauth Social Application, not in Git.
The project does not automatically read `client_secret.json` or Google credential
environment variables. The client credentials and Site association are stored in
the local database and must be configured for a fresh installation.

New student accounts follow the existing approval workflow. Pending students and
deactivated accounts cannot log in; an administrator must update their status.
Authorized users are routed through `/dashboard/` to their role dashboard.

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
