"""Client for the Open Library Covers API — high-resolution cover fallback.

Google Books only returns small thumbnails, so we fetch a large cover from Open
Library by ISBN when one exists.
"""
import requests

OPEN_LIBRARY_COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"


class OpenLibraryCoversClient:
    def __init__(self, session=None, timeout=10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def cover_url(self, isbn, size='L'):
        """Build the cover URL for an ISBN. `size` is one of 'S', 'M', 'L'."""
        if not isbn:
            return ''
        return OPEN_LIBRARY_COVER_URL.format(isbn=isbn, size=size)

    def has_cover(self, isbn, size='L'):
        """Return True if Open Library actually has a cover for this ISBN.

        Appending ``?default=false`` makes the API return 404 (instead of a blank
        placeholder image) when no cover exists, so the status code is a reliable
        existence check.
        """
        if not isbn:
            return False
        url = self.cover_url(isbn, size) + "?default=false"
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            return response.status_code == 200
        except requests.RequestException:
            return False
