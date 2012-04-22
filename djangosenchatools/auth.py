from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login


class SettingUserBackend(object):
    """
    Authenticate automatically as the ``static_username`` user
    that :class:`SettingUserMiddleware` sends to this backend.
    """
    supports_inactive_user = False

    def authenticate(self, static_username=None):
        assert static_username == settings.SENCHATOOLS_USER, "This should not happen! Have you enabled SettingUserMiddleware?"
        user = self.get_user(static_username)
        return user


    def get_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None


class SettingUserMiddleware(object):
    """
    Authenticate as ``settings.SENCHATOOLS_USER``. Expects
    :class:`SettingUserBackend` to be in ``settings.AUTHENTICATION_BACKENDS``.
    """
    def process_request(self, request):
        if not hasattr(settings, 'SENCHATOOLS_USER'):
            raise ImproperlyConfigured('SettingUserMiddleware requires SENCHATOOLS_USER in settings.')

        user = authenticate(static_username=settings.SENCHATOOLS_USER)
        if user:
            request.user = user
            login(request, user)
