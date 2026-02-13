"""Configurações de CORS."""
import os

CORS_ALLOWED_ORIGINS = [
    # Local development
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    # Production - Vercel frontend
    'https://enviador-6xy3gk61t-gustavo-faria-cardosos-projects.vercel.app',
    # Allow any Vercel deployment via environment variable
    os.getenv('FRONTEND_URL', 'https://enviador-6xy3gk61t-gustavo-faria-cardosos-projects.vercel.app'),
]

# Remove duplicates and filter out None values
CORS_ALLOWED_ORIGINS = list(filter(None, set(CORS_ALLOWED_ORIGINS)))

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_EXPOSE_HEADERS = [
    'content-type',
    'x-csrftoken',
    'authorization',
]
