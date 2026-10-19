# Deploy ClubTrack to Vercel Hobby

This keeps the Flask application, Supabase database, and existing administrator login. Vercel runs `index:app` using Python 3.12. `index.py` calls the existing factory; there is no Flask development server in production. `public/static` is served by Vercel's CDN, and Flask serves the same path locally. Templates remain bundled with the function.

## 1. Prepare production credentials locally

Keep your `.env` private. It is excluded from Git and Vercel uploads. Never paste credentials into GitHub files, issues, or chat.

In your local terminal, generate a new session secret:

```sh
.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

Copy that result directly into Vercel's `SECRET_KEY` field when configuring the deployment. Keep the same value across instances/redeployments; changing it signs everyone out. Do not use a randomly generated secret on every function invocation.

Generate a hash of a new administrator password:

```sh
.venv/bin/python -c 'from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass("New production admin password: ")))'
```

Copy the entire result into Vercel's `ADMIN_PASSWORD_HASH` field. Use the password you entered to log in, not the hash. The public local `demo-password` is deliberately rejected on Vercel. Local demo settings are unchanged.

## 2. Push the source to GitHub

Create an empty repository under your personal GitHub account. From this project directory:

```sh
git add .
git diff --cached --name-only
```

Confirm `.env`, `.venv`, and `.vercel` are absent from the staged file list, then:

```sh
git commit -m "Prepare ClubTrack Flask app for Vercel"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/clubtrack.git
git push -u origin main
```

If cloning the project elsewhere without Git metadata, first run `git init`. GitHub Actions runs tests on pushes and pull requests without production secrets. Vercel deployments run independently of GitHub Actions; confirm tests pass before publishing.

## 3. Import into Vercel

1. Sign in to Vercel and use your personal **Hobby** account.
2. Choose **Add New → Project**, connect GitHub, and import the repository.
3. Use the repository root as Root Directory and **Flask** as Framework Preset. Leave Build Command and Output Directory at their defaults; no frontend build is needed.
4. Before deploying, add the following Environment Variables for **Production**:

| Name | Value |
| --- | --- |
| `SECRET_KEY` | Your new random secret from step 1; at least 32 characters |
| `ADMIN_USERNAME` | Your chosen admin username, such as `admin` |
| `ADMIN_PASSWORD_HASH` | The entire generated password hash, without surrounding quotes |
| `SUPABASE_URL` | Your Supabase HTTPS Project URL |
| `SUPABASE_SECRET_KEY` | Your Supabase `sb_secret_...` key, or legacy `service_role` key |
| `COOKIE_SECURE` | `true` |

Find the Project URL in Supabase's **Connect** dialog. Find or create a secret key in **Settings → API Keys → Publishable and secret API keys**. A publishable/anon key cannot access the tables with the current SQL permissions. Supabase's Data API must be enabled for the public schema. Your existing tables need no migration; do not rerun `schema.sql` over them.

Enter environment values without `.env`-style quotes. Vercel supplies `VERCEL=1` automatically. Secure cookies and debug-off are enforced on Vercel even if `COOKIE_SECURE=false` is accidentally entered. The server sends HttpOnly, SameSite=Lax cookies and HSTS, checks CSRF tokens on writes, and uses an eight-hour session expiry. No filesystem writes or in-memory session store are used in production. The Supabase privileged key is only used in server-to-server requests.

5. Click **Deploy**. Open the resulting HTTPS URL. Later environment-variable changes require a redeployment.

For Preview deployments, add separate Preview variables only if needed, preferably pointing to a separate Supabase project with demo data. Do not expose production credentials to untrusted preview branches. Preview login also requires HTTPS and a non-demo admin password. For login abuse controls, configure a Vercel Firewall rule for POST `/login`; there is no application-level distributed login rate limiter.

## 4. Verify the deployment

1. Confirm the login page is styled and an unauthenticated visit to `/` redirects to `/login`.
2. Sign in using your chosen username and password.
3. Create a test event, add a student, and mark the student present. Confirm the total and percentage update.
4. Refresh and sign out/in; confirm the data persists in Supabase.
5. After signing out, confirm the events page requires login again.

If startup fails, inspect Vercel runtime logs for a missing variable or rejected demo password. If a database error appears, check the server secret key, Data API, tables, and Supabase project availability. If login loops, verify HTTPS, a stable `SECRET_KEY`, and cookies enabled. No Supabase Auth redirect URL is needed because this application uses its own admin session.

Tests mock the Supabase API. They verify login, session portability between app instances, cookie flags, CSRF, rendering, and writes; they do not verify a deployed function or live database. The final checks above require the actual deployment.

Hobby is intended for personal, non-commercial projects and has usage limits. A personal training demo fits that purpose; review current terms and usage in your dashboard.

Sources: [Flask on Vercel](https://vercel.com/docs/frameworks/backend/flask), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [Hobby plan](https://vercel.com/docs/plans/hobby), [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys).
