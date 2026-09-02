from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Lets the DRF browsable API's login page work for manual testing in a
# browser. JWT stays the only auth method in base.py (and therefore in
# production); session auth is dev-only.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_AUTHENTICATION_CLASSES': REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] + (
        'rest_framework.authentication.SessionAuthentication',
    ),
}
