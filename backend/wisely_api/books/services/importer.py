"""Orchestration: turn Google Books results into persisted Book rows (with covers)."""
from django.utils import timezone

from books.models import Book
from core.models import Category

from .covers import resolve_cover
from .google_books import GoogleBooksClient


def import_book_from_volume(volume, *, open_library=None):
    """Create or update a Book from a normalized Google volume dict.

    Returns ``(book, created)``.
    """
    if not volume.get('google_books_id'):
        raise ValueError("Cannot import a volume without a google_books_id")

    cover_url, cover_source = resolve_cover(volume, open_library=open_library)

    book, created = Book.objects.update_or_create(
        google_books_id=volume['google_books_id'],
        defaults={
            'title': volume.get('title', ''),
            'subtitle': volume.get('subtitle', ''),
            'author': volume.get('author', ''),
            'description': volume.get('description', ''),
            'publisher': volume.get('publisher', ''),
            'published_date': volume.get('published_date', ''),
            'year_published': volume.get('year_published'),
            'page_count': volume.get('page_count'),
            'language': volume.get('language', ''),
            'isbn': volume.get('isbn', ''),
            'isbn_10': volume.get('isbn_10', ''),
            'thumbnail_url': volume.get('thumbnail_url', ''),
            'cover_url': cover_url,
            'cover_source': cover_source,
            'google_average_rating': volume.get('average_rating'),
            'google_ratings_count': volume.get('ratings_count'),
            'info_link': volume.get('info_link', ''),
            'last_synced_at': timezone.now(),
        },
    )

    category_names = volume.get('categories') or []
    if category_names:
        categories = [Category.objects.get_or_create(name=name)[0] for name in category_names]
        book.categories.set(categories)

    return book, created


def import_book(query, *, client=None, open_library=None, limit=1):
    """Search Google Books for ``query`` and import the top ``limit`` result(s).

    Returns a list of ``(book, created)`` tuples.
    """
    client = client or GoogleBooksClient()
    volumes = client.search(query, max_results=limit)
    return [
        import_book_from_volume(volume, open_library=open_library)
        for volume in volumes
        if volume.get('google_books_id')
    ]
