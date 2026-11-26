from pathlib import Path
import os
import ctypes
from django.core.exceptions import ImproperlyConfigured
import dj_database_url


os.environ["GDAL_LIBRARY_PATH"] = "/opt/homebrew/lib/libgdal.dylib"
os.environ["LD_LIBRARY_PATH"] = "/opt/homebrew/lib"
# Optional GDAL/PROJ locations for local macOS development (set them in .env if needed)
for _var in ("DYLD_LIBRARY_PATH", "PROJ_LIB", "PROJ_LIBRARY_PATH"):
    if os.getenv(_var):
        os.environ[_var] = os.getenv(_var)

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-change-me')
ORS_API_KEY = os.getenv('ORS_API_KEY', '')
OCM_API_KEY = os.getenv('OCM_API_KEY', '')

AI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
AI_API_KEY = os.getenv('AI_API_KEY', '')
AI_MODEL_NAME = "gemini-1.5-flash"


DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'


STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-change-me')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')


SESSION_COOKIE_AGE = 87000

CART_SESSION_ID = 'cart' 


INSTALLED_APPS = [
    'daphne',
    'baton',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'widget_tweaks',
    'whitenoise.runserver_nostatic',
    'core',
    'product',
    'cart',
    'order',
    'charge_stations',
    'django.contrib.gis',
    'rest_framework',
    'api',
    'marketplace',
    'forum',
    'transport',
    'administration',
    'django_apscheduler',
    'channels',
    'baton.autodiscover',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vivasonya.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.favorites_context',
                'cart.context_processors.cart_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'vivasonya.wsgi.application'

ASGI_APPLICATION = 'vivasonya.asgi.application'

CHANNEL_LAYERS = {
    "default": {


        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {

            "hosts": [("127.0.0.1", 6379)],


        },



    },
}



DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.getenv('POSTGRES_PORT', 5432),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', '1'),
        'NAME': os.getenv('POSTGRES_NAME', "projectdb")

    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'uk' 
TIME_ZONE = 'Europe/Kiev' # Встановлюємо часовий пояс
USE_I18N = True
USE_L10N = True
USE_TZ = True  

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'







try:
    lib_path = os.environ.get("GDAL_LIBRARY_PATH")
    print(f"GDAL_LIBRARY_PATH из настроек: {lib_path}")
    
    if not lib_path:
        raise ImproperlyConfigured("GDAL_LIBRARY_PATH не установлен.")

    lib = ctypes.CDLL(lib_path)
    print("GDAL успешно загружен!")
except Exception as e:
    print(f"Ошибка загрузки GDAL: {e}")


try:
    proj_lib_path = os.environ.get("PROJ_LIB")
    print(f"PROJ_LIB из настроек: {proj_lib_path}")

    if not proj_lib_path:
        raise ImproperlyConfigured("PROJ_LIB не установлен.")

    proj_db_path = os.path.join(proj_lib_path, "proj.db")
    print(f"Ожидаемый путь к proj.db: {proj_db_path}")

    if not os.path.isfile(proj_db_path):
        raise ImproperlyConfigured(f"Файл proj.db не найден по пути: {proj_db_path}")

    lib_proj = ctypes.CDLL("libproj.so" if os.name != "nt" else "proj.dll")
    print("PROJ успешно загружен!")
except Exception as e:
    print(f"Ошибка загрузки PROJ: {e}")

import logging

logger = logging.getLogger(__name__)

logger.debug(f"PROJ_LIB: {os.environ.get('PROJ_LIB')}")
logger.debug(f"GDAL_LIBRARY_PATH: {os.environ.get('GDAL_LIBRARY_PATH')}")



BATON = {
    'SITE_HEADER': 'ElectroHub Admin',
    'SITE_TITLE': 'ElectroHub Панель керування',
    'INDEX_TITLE': 'Ласкаво просимо до панелі керування ElectroHub',
    'SUPPORT_HREF': '/help',
    'COPYRIGHT': '© 2025 ElectroHub. Всі права захищено.',
    'POWERED_BY': '<a href="https://github.com/otto-torino/django-baton">Django Baton</a>',
    'CONFIRM_UNSAVED_CHANGES': True,
    'SHOW_MULTIPART_UPLOADING_PROGRESS': True,
    'ENABLE_IMAGES_PREVIEW': True,
    'CHANGELIST_FILTERS_IN_MODAL': True,
    'CHANGELIST_FILTERS_ALWAYS_OPEN': False,
    'MENU_ALWAYS_COLLAPSED': False,
    'GRAVATAR_ENABLED': True,

    'GRAVATAR_DEFAULT_IMAGE': 'mp',


    'THEME': {

        '--baton-primary': '#facc15',
        '--baton-primary-hover': '#eab308',


        '--baton-navbar-bg': '#000000',
        '--baton-navbar-color': '#ededed',
        '--baton-navbar-color-hover': '#facc15',


        '--baton-sidebar-bg': '#ffffff',
        '--baton-sidebar-color': '#0f172a',
        '--baton-sidebar-color-hover': '#facc15',
        '--baton-sidebar-active-bg': '#facc15',
        '--baton-sidebar-active-color': '#0f172a',


        '--baton-body-bg': '#f9fafb',
        '--baton-body-color': '#0f172a',


        '--baton-light': '#ffffff',
        '--baton-light-hover': '#f9fafb',
        '--baton-dark': '#0f172a',


        '--baton-border-radius': '0.5rem',
        '--baton-box-shadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    },
    'CONTAINER_FLUID': True,

}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_USE_SESSIONS = False
CSRF_COOKIE_NAME = 'csrftoken'