"""Vercel WSGI entry point; routes remain in the existing application factory."""
from app import create_app

app = create_app()
