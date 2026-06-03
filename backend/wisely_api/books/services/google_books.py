"""Client + normalizer for the Google Books API — Wisely's primary book-data engine.

Google Books drives search and text metadata (descriptions, page counts, publisher,
language) and supplies the aggregated "audience" rating (averageRating/ratingsCount).
"""
import requests
from django.conf import settings

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksError(Exception):
    """Raised when a Google Books API request fails."""


def _extract_isbns(industry_identifiers):
    isbn_13 = isbn_10 = ''
    for ident in industry_identifiers or []:
        if ident.get('type') == 'ISBN_13':
            isbn_13 = ident.get('identifier', '')
        elif ident.get('type') == 'ISBN_10':
            isbn_10 = ident.get('identifier', '')
    return isbn_13, isbn_10


def _parse_year(published_date):
    if published_date and len(published_date) >= 4 and published_date[:4].isdigit():
        return int(published_date[:4])
    return None


def normalize_volume(volume):
    """Flatten a Google Books `volume` resource into a plain dict the importer understands."""
    info = volume.get('volumeInfo', {})
    isbn_13, isbn_10 = _extract_isbns(info.get('industryIdentifiers'))
    image_links = info.get('imageLinks', {})
    authors = info.get('authors', [])

    return {
        'google_books_id': volume.get('id', ''),
        'title': info.get('title', ''),
        'subtitle': info.get('subtitle', ''),
        'author': ', '.join(authors),
        'authors': authors,
        'description': info.get('description', ''),
        'publisher': info.get('publisher', ''),
        'published_date': info.get('publishedDate', ''),
        'year_published': _parse_year(info.get('publishedDate', '')),
        'page_count': info.get('pageCount'),
        'language': info.get('language', ''),
        'categories': info.get('categories', []),
        'isbn_13': isbn_13,
        'isbn_10': isbn_10,
        'isbn': isbn_13 or isbn_10,
        'thumbnail_url': image_links.get('thumbnail') or image_links.get('smallThumbnail', ''),
        'average_rating': info.get('averageRating'),
        'ratings_count': info.get('ratingsCount'),
        'info_link': info.get('infoLink', ''),
    }


class GoogleBooksClient:
    def __init__(self, api_key=None, session=None, timeout=10, country='US'):
        self.api_key = api_key if api_key is not None else getattr(settings, 'GOOGLE_BOOKS_API_KEY', '')
        self.session = session or requests.Session()
        self.timeout = timeout
        self.country = country

    def _params(self, **params):
        if self.api_key:
            params['key'] = self.api_key
        if self.country:
            # Google now requires a country for many anonymous requests.
            params['country'] = self.country
        return params

    def _get(self, url, **params):
        try:
            response = self.session.get(url, params=self._params(**params), timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise GoogleBooksError(str(exc)) from exc

    def search(self, query, max_results=10):
        data = self._get(GOOGLE_BOOKS_API_URL, q=query, maxResults=max_results)
        return [normalize_volume(item) for item in data.get('items', [])]

    def get_volume(self, volume_id):
        return normalize_volume(self._get(f"{GOOGLE_BOOKS_API_URL}/{volume_id}"))

    def get_by_isbn(self, isbn):
        results = self.search(f"isbn:{isbn}", max_results=1)
        return results[0] if results else None
