"""Resolve the best cover for a book across Google Books and Open Library.

Google Books only ever returns small, low-resolution thumbnails, so when an ISBN
has a cover on Open Library we prefer that high-resolution image and fall back to
the (https-normalized) Google thumbnail otherwise.
"""
from django.conf import settings

from .open_library import OpenLibraryCoversClient

GOOGLE = 'google'
OPENLIBRARY = 'openlibrary'


def _upgrade_google_thumbnail(url):
    """Make a Google thumbnail URL a little better: force https, drop the page-curl overlay."""
    if not url:
        return ''
    return url.replace('http://', 'https://').replace('&edge=curl', '')


def resolve_cover(volume, *, open_library=None, policy=None):
    """Return ``(cover_url, source)`` for a normalized Google volume dict.

    Policies (``settings.BOOK_COVER_POLICY``):
      - ``'auto'`` (default): prefer Open Library's high-res cover when the ISBN has
        one, else use the Google thumbnail.
      - ``'openlibrary_only'``: only ever use Open Library; no Google fallback.
    """
    policy = policy or getattr(settings, 'BOOK_COVER_POLICY', 'auto')
    open_library = open_library or OpenLibraryCoversClient()
    isbn = volume.get('isbn')
    google_thumbnail = volume.get('thumbnail_url', '')

    if isbn and open_library.has_cover(isbn):
        return open_library.cover_url(isbn, 'L'), OPENLIBRARY

    if policy == 'openlibrary_only':
        return '', ''

    if google_thumbnail:
        return _upgrade_google_thumbnail(google_thumbnail), GOOGLE

    return '', ''
