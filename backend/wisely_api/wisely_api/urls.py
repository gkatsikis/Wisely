"""
URL configuration for wisely_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import GoogleLogin

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include('allauth.urls')),  # allauth web flows + social callbacks
    path('api/auth/', include('dj_rest_auth.urls')),  # login, logout, user, password, token refresh
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),  # signup
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),

    # API
    path('api/', include('core.urls')),
    path('api/books/', include('books.urls')),
    path('api/reviews/', include('books.review_urls')),
    path('api/clinicians/', include('clinicians.urls')),
    path('api/seekers/', include('seekers.urls')),
    path('api/engagement/', include('engagement.urls')),
    path('api/', include('readinglists.urls')),  # /api/reading-lists/ + /api/shared-lists/{token}/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
