# Student Club Attendance Tracker

A small Flask app with server-rendered HTML, responsive CSS, and Supabase Postgres storage. One club administrator can create events, add students, and mark attendance. No JavaScript build step is needed.

## 1. Install locally

Requires Python 3.10+ and a Supabase project.

```sh
cd /Users/shreelakshyareddi/attendanceTracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\activate` and copy the example using your file manager.

## Interactive configuration (recommended)

Run `.venv/bin/python scripts/configure.py` in your local terminal. Find your Project URL in the Supabase Connect dialog, and a secret key under Settings > API Keys > Publishable and secret API keys. The script privately prompts for the key and administrator password, writes the password hash into `.env`, and preserves an existing Flask secret. It prints no secrets and restricts `.env` to owner read/write. Do not share `.env` or commit it; `.gitignore` excludes it. The manual steps below are an alternative.

## 2. Set up Supabase

Create a Supabase project, open its SQL Editor, and run the contents of `schema.sql` once. This creates `events` and `attendance`, their constraints, and access restrictions. The Data API must be enabled for the public schema.

Find your project URL and secret API key in your project's Connect dialog or API settings. Set these values in `.env`:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key
```

Use a new `sb_secret_...` key or a legacy `service_role` key. Do not use a publishable or anon key. The secret stays on the Flask server and must never appear in HTML, browser code, or source control. Supabase documents key types at https://supabase.com/docs/guides/getting-started/api-keys.

## 3. Configure the administrator

Generate a session secret:

```sh
python -c 'import secrets; print(secrets.token_hex(32))'
```

Paste the output into `SECRET_KEY` in `.env`.

Generate a password hash (your password is entered privately):

```sh
python -c 'from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass("Admin password: ")))'
```

Paste that output into `ADMIN_PASSWORD_HASH` in `.env`. Set `ADMIN_USERNAME` to your preferred username. Keep `COOKIE_SECURE=false` for local HTTP; use `true` with HTTPS hosting. There is no default password. To reset the administrator password, generate a new hash, update `.env`, and restart Flask.

## 4. Run

```sh
source .venv/bin/activate
python app.py
```

Open http://127.0.0.1:5000 and sign in with your configured administrator credentials. Keep this terminal running; press Ctrl+C to stop. If port 5000 is busy:

```sh
flask --app 'app:create_app()' run --port 5001
```

Create an event, open it, and add students using their names and student IDs. IDs are unique within each event and case-sensitive. New students start absent. Click **Mark present** or **Mark absent** to update them. All event and roster data is saved immediately to Supabase and remains after restarting Flask.

Attendance percentage = present students / total students × 100, rounded to a whole number. Empty events show 0%. Students are stored per event; there is no separate global student directory.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests use mocked Supabase responses, so no real credentials or database are needed. They cover login protection, CSRF, event creation, roster rendering, attendance updates, duplicate students, and database failures. For a real database check, create an event and student, mark them present, restart the app, and confirm the saved records remain.

## Files and security

- `app.py`: configuration, administrator session, validation, routes, Supabase REST calls.
- `templates/`: HTML pages; `public/static/style.css`: styles.
- `schema.sql`: database tables and permissions.
- `.env.example`: configuration template; `.env` is ignored by Git.

Password hashes, signed sessions, CSRF tokens, and server-side data access protect this local app. RLS is enabled with no public access policies; only the server's privileged Supabase key accesses attendance. Sessions expire after eight hours. This is a single-admin local application; use Vercel’s managed WSGI runtime for deployment; configure a Vercel Firewall rule for POST /login if you need login rate limiting. Debug mode is off.

If startup reports a missing setting, complete `.env`. If the app shows a database connection error, verify the URL/key, run the SQL, enable the Data API, and check network connectivity. Re-running the schema against existing tables will fail deliberately; it does not erase existing data.

## Local demo login

The local `.env` has been configured with username `admin` and password `demo-password` for this demo. You can skip manual administrator hash generation. These credentials are for local demonstration only. Supabase credentials still need to be configured separately.

## Deploy to Vercel

See [DEPLOYMENT.md](DEPLOYMENT.md) for GitHub, production environment variables, and Hobby deployment steps.
