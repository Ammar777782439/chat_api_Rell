"""
WSGI config for chat_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from dotenv import load_dotenv # استيراد load_dotenv

from django.core.wsgi import get_wsgi_application

load_dotenv() # تحميل المتغيرات من ملف .env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_app.settings')

application = get_wsgi_application()
