from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.http import JsonResponse


def health(request):
    return JsonResponse({'status': 'ok'})


class GoogleLogin(SocialLoginView):
    """Exchange a Google OAuth credential (sent by the React/Next.js or mobile client)
    for Wisely JWTs. Accepts an ``access_token`` or an auth ``code``."""

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
