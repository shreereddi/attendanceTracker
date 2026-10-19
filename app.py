import hmac
import os
import secrets
from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

if not os.getenv('VERCEL'):
    load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__, static_folder='public/static', static_url_path='/static')
    hosted = os.getenv('VERCEL') == '1'
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        ADMIN_USERNAME=os.getenv('ADMIN_USERNAME', 'admin'),
        ADMIN_PASSWORD_HASH=os.getenv('ADMIN_PASSWORD_HASH'),
        SUPABASE_URL=os.getenv('SUPABASE_URL', '').rstrip('/'),
        SUPABASE_SECRET_KEY=os.getenv('SUPABASE_SECRET_KEY'),
        DEBUG=False,
        SESSION_COOKIE_NAME='clubtrack_session',
        SESSION_REFRESH_EACH_REQUEST=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if hosted:
        app.config.update(SESSION_COOKIE_SECURE=True, DEBUG=False)
    for key in ('SECRET_KEY', 'ADMIN_PASSWORD_HASH', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY'):
        if not app.config.get(key) or app.config[key].startswith('replace-'):
            raise RuntimeError(f'Missing {key}. Follow README.md to configure .env.')
    if len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('SECRET_KEY must contain at least 32 characters.')
    if app.config['SUPABASE_SECRET_KEY'].startswith('sb_publishable_'):
        raise RuntimeError('SUPABASE_SECRET_KEY must be a server secret key, not a publishable key.')
    if hosted and check_password_hash(app.config['ADMIN_PASSWORD_HASH'], 'demo-password'):
        raise RuntimeError('Set a new ADMIN_PASSWORD_HASH for deployment; the local demo password is public.')
    if urlparse(app.config['SUPABASE_URL']).scheme != 'https':
        raise RuntimeError('SUPABASE_URL must use HTTPS.')

    def db(method, table, params=None, payload=None):
        key = app.config['SUPABASE_SECRET_KEY']
        headers = {'apikey': key, 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        # Legacy service_role keys are JWTs; newer sb_secret keys use apikey only.
        if not key.startswith('sb_secret_'):
            headers['Authorization'] = f'Bearer {key}'
        response = requests.request(method, f"{app.config['SUPABASE_URL']}/rest/v1/{table}",
                                    headers=headers, params=params, json=payload, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else []

    def protected(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get('admin'):
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    @app.before_request
    def csrf_check():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        if request.method == 'POST' and not hmac.compare_digest(
                session['csrf_token'].encode(), request.form.get('csrf_token', '').encode()):
            abort(400, 'Your form expired. Refresh the page and try again.')

    @app.after_request
    def security_headers(response):
        if hosted:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.errorhandler(requests.RequestException)
    def database_error(error):
        app.logger.error('Supabase request failed (%s)', type(error).__name__)
        return render_template('error.html', message='Unable to reach the database. Check your Supabase settings and SQL setup, then try again.'), 503

    def event_or_404(event_id):
        rows = db('GET', 'events', {'id': f'eq.{event_id}', 'select': '*'})
        if not rows:
            abort(404)
        return rows[0]

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username_ok = hmac.compare_digest(request.form.get('username', '').encode(), app.config['ADMIN_USERNAME'].encode())
            password_ok = check_password_hash(app.config['ADMIN_PASSWORD_HASH'], request.form.get('password', ''))
            if username_ok and password_ok:
                session.clear()
                session['admin'] = True
                session['csrf_token'] = secrets.token_hex(32)
                session.permanent = True
                return redirect(url_for('index'))
            flash('Invalid username or password.', 'error')
        return render_template('login.html')

    @app.post('/logout')
    @protected
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @protected
    def index():
        events = db('GET', 'events', {'select': '*,attendance(status)', 'order': 'event_date.desc,created_at.desc'})
        for event in events:
            rows = event.pop('attendance', [])
            event['total'] = len(rows)
            event['present'] = sum(row['status'] == 'present' for row in rows)
            event['percent'] = round(100 * event['present'] / len(rows)) if rows else 0
        return render_template('index.html', events=events)

    @app.post('/events')
    @protected
    def create_event():
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        try:
            event_date = date.fromisoformat(request.form.get('event_date', '')).isoformat()
        except ValueError:
            flash('Enter a valid event date.', 'error')
            return redirect(url_for('index'))
        if not (1 <= len(name) <= 150 and 1 <= len(location) <= 200):
            flash('Enter an event name (up to 150 characters) and location (up to 200).', 'error')
            return redirect(url_for('index'))
        event = db('POST', 'events', payload={'name': name, 'event_date': event_date, 'location': location})[0]
        flash('Event created. Add your students below.', 'success')
        return redirect(url_for('event_detail', event_id=event['id']))

    @app.get('/events/<uuid:event_id>')
    @protected
    def event_detail(event_id):
        event = event_or_404(event_id)
        students = db('GET', 'attendance', {'event_id': f'eq.{event_id}', 'select': '*', 'order': 'student_name.asc'})
        present = sum(student['status'] == 'present' for student in students)
        return render_template('event.html', event=event, students=students, present=present,
                               percent=round(100 * present / len(students)) if students else 0)

    @app.post('/events/<uuid:event_id>/students')
    @protected
    def add_student(event_id):
        event_or_404(event_id)
        name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        if not (1 <= len(name) <= 150 and 1 <= len(student_id) <= 80):
            flash('Enter a student name and a unique student ID.', 'error')
        else:
            try:
                db('POST', 'attendance', payload={'event_id': str(event_id), 'student_name': name, 'student_id': student_id, 'status': 'absent'})
                flash('Student added and marked absent. Update their attendance when they arrive.', 'success')
            except requests.HTTPError as error:
                if error.response is not None and error.response.status_code == 409:
                    flash('That student ID is already on this event’s roster.', 'error')
                else:
                    raise
        return redirect(url_for('event_detail', event_id=event_id))

    @app.post('/events/<uuid:event_id>/attendance/<uuid:attendance_id>')
    @protected
    def update_attendance(event_id, attendance_id):
        status = request.form.get('status')
        if status not in ('present', 'absent'):
            abort(400)
        rows = db('PATCH', 'attendance', {'id': f'eq.{attendance_id}', 'event_id': f'eq.{event_id}'}, {'status': status})
        if not rows:
            abort(404)
        return redirect(url_for('event_detail', event_id=event_id))

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000)
