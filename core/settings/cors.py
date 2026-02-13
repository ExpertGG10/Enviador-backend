"""Configurações de CORS."""
import os
import re

# Static allowed origins
CORS_ALLOWED_ORIGINS = [
    # Local development
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
]

# Add frontend URL from environment variable if set
FRONTEND_URL = os.getenv('FRONTEND_URL')
if FRONTEND_URL:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)

# Remove duplicates
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS))

# Allow any Vercel preview/production deployment (e.g., enviador-*.vercel.app)
# This regex matches: https://enviador-<anything>.vercel.app
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://enviador-[\w-]+\.vercel\.app$",
]

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
