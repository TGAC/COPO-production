# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from os import environ
from django.conf import settings
from django.contrib.messages import constants as messages
from datetime import timedelta
from common.utils import helpers as resolve_env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SCHEMA_DIR = os.path.join(BASE_DIR, 'common', 'schemas')

SCHEMA_VERSIONS_DIR = os.path.join(BASE_DIR, 'common', 'schema_versions')

SCHEMA_VERSIONS_FILE_LIST = ["sample.json", "ena_seq.json"]  # files based on schema versions

MANIFEST_PATH = os.path.join(BASE_DIR, 'static', 'assets', 'manifests')
MANIFEST_FILE_NAME = "{0}_MANIFEST_TEMPLATE{1}.xlsx"
MANIFEST_DOWNLOAD_URL =  "/static/assets/manifests/" + MANIFEST_FILE_NAME

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

PROFILE_LOG_BASE = os.path.join(BASE_DIR, 'profiler')
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = resolve_env.get_env('SECRET_KEY')

LOGIN_URL = '/accounts/auth/'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if str(resolve_env.get_env('DEBUG')).lower() == 'true' else False

# ALLOWED_HOSTS = [ gethostname(), gethostbyname(gethostname()), ]
ALLOWED_HOSTS = ['127.0.0.1', '0.0.0.0', '.copo-project.org',
                 '.demo.copo-project.org', 'localhost', '.copodev.cyverseuk.org']
ALLOWED_CIDR_NETS = ['10.0.0.0/24']
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://0.0.0.0:8000",
    "http://0.0.0.0:80",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",    
    "https://copo-project.org",
    "http://demo.copo-project.org",
    "https://copodev.cyverseuk.org"

]
DEBUG_PROPAGATE_EXCEPTIONS = True


# Django's base applications definition
DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# user-defined applications definition
PROJECT_APPS = [
    'channels',
    'src.apps.copo_core',
    'src.apps.copo_profile',
    'src.apps.copo_sample',
    'src.apps.copo_login',
    'src.apps.copo_dtol_upload',
    'src.apps.copo_dtol_submission',
    'src.apps.copo_landing_page',
    'src.apps.copo_read_submission',
    'src.apps.copo_assembly_submission',
    'src.apps.copo_seq_annotation_submission',
    'src.apps.copo_barcoding_submission',
    'src.apps.copo_file',
    'src.apps.copo_accession',
    'src.apps.copo_tol_dashboard',
    'src.apps.copo_manifest_wizard',
    'src.apps.api',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    'rest_framework',
    'rest_framework.authtoken',
    'compressor',
    'django_extensions',
    'corsheaders',
    'crispy_forms',
    "crispy_bootstrap5"
]
INSTALLED_APPS = DJANGO_APPS + PROJECT_APPS
ASGI_APPLICATION = 'src.main_config.asgi.application'
#WSGI_APPLICATION = 'src.main_config.wsgi.application'

#CRISPY_TEMPLATE_PACK = 'uni-form'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
# sass, social accounts...
sass_exe = '/usr/local/bin/sass'
COMPRESS_PRECOMPILERS = (
    ('text/scss', sass_exe + ' --scss  {infile} {outfile}'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
)

SOCIALACCOUNT_PROVIDERS = \
    {'google':
         {'SCOPE': ['profile', 'email'],
          'AUTH_PARAMS': {'access_type': 'online'}}}

MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_tools.middlewares.ThreadLocal.ThreadLocalMiddleware',
    'compression_middleware.middleware.CompressionMiddleware',
    'src.apps.copo_core.middlewares.LocksMiddleware.LocksMiddleware',
    'src.apps.copo_core.middlewares.LogUncaughtExceptions.LogUncaughtExceptions',
    'allow_cidr.middleware.AllowCIDRMiddleware'
]

AUTHENTICATION_BACKENDS = (
    # Needed to auth by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as auth by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',

    )
}

CORS_ORIGIN_WHITELIST = (
    'http://localhost:8000',
    'http://0.0.0.0:8000',
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8001',
)
# CORS_ORIGIN_ALLOW_ALL = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/copo/auth/login'



LOGIN_URL = '/copo/auth/login'



# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Etc/GMT+0'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# CSRF_TRUSTED_ORIGINS = ['http://*.copo-project.org', 'https://*.copo-project.org', '127.0.0.1:8000']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

# print(STATICFILES_DIRS)
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, resolve_env.get_env('MEDIA_PATH'))
MEDIA_URL = 'media/'

ELASTIC_SEARCH_URL = 'http://localhost:9200/ontologies/plant_ontology/_search'

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 48 * 60 * 60  #

SITE_ID = 1

COPO_URL = 'copo-project.org'


DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024 * 2
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 24

#CACHES = {
#    'default': {
#        'LOCATION': 'copo_cache_table',
#        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#
#    }
#}



VIEWLOCK_TIMEOUT = timedelta(seconds=1800)

# Enables django-html-validator that automatically checks if the served HTML pages are
# valid for the W3C checkers.
HTMLVALIDATOR_ENABLED = True
HTMLVALIDATOR_VNU_JAR = './tests/utilities/vnu.jar'
HTMLVALIDATOR_DUMPDIR = os.path.join(BASE_DIR, 'html_validators')

# Warning: Auto-created primary key used when not defining a primary key type, by default 'django.db.models.AutoField'.
# Solution: Set 'django.db.models.AutoField'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

TEMPLATES = [

    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
            #
            os.path.join( BASE_DIR, 'src', 'apps', 'copo_landing_page', 'templates'),
            os.path.join( BASE_DIR, 'src', 'apps', 'copo_core', 'templates', 'copo'),
            os.path.join( BASE_DIR, 'static', 'swagger'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'src.apps.copo_core.copo_user_status_messages.latest_message'
            ],
            'debug':  DEBUG,
        },
    },
]

ROOT_URLCONF = 'src.main_config.urls'

UPLOAD_PATH = os.path.join(settings.MEDIA_ROOT,'uploads')