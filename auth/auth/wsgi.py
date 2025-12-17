"""
WSGI config for auth project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from django.core.wsgi import get_wsgi_application

# Change from 'auth.auth.settings' to 'auth.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth.settings')

application = get_wsgi_application()