from django.test import SimpleTestCase

from books.services.covers import _upgrade_google_thumbnail, resolve_cover
from books.services.google_books import normalize_volume

SAMPLE_VOLUME = {
    'id': 'abc123',
    'volumeInfo': {
        'title': 'The Body Keeps the Score',
        'subtitle': 'Brain, Mind, and Body in the Healing of Trauma',
        'authors': ['Bessel van der Kolk'],
        'publisher': 'Penguin',
        'publishedDate': '2014-09-25',
        'description': 'A landmark book about trauma.',
        'pageCount': 464,
        'categories': ['Psychology'],
        'averageRating': 4.5,
        'ratingsCount': 1200,
        'language': 'en',
        'industryIdentifiers': [
            {'type': 'ISBN_10', 'identifier': '0143127748'},
            {'type': 'ISBN_13', 'identifier': '9780143127741'},
        ],
        'imageLinks': {
            'smallThumbnail': 'http://books.google.com/books/content?id=abc123&zoom=5&edge=curl',
            'thumbnail': 'http://books.google.com/books/content?id=abc123&zoom=1&edge=curl',
        },
        'infoLink': 'https://books.google.com/books?id=abc123',
    },
}


class _FakeOpenLibrary:
    def __init__(self, has=True):
        self._has = has

    def has_cover(self, isbn, size='L'):
        return self._has

    def cover_url(self, isbn, size='L'):
        return f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"


class NormalizeVolumeTests(SimpleTestCase):
    def test_flattens_core_fields(self):
        data = normalize_volume(SAMPLE_VOLUME)
        self.assertEqual(data['google_books_id'], 'abc123')
        self.assertEqual(data['author'], 'Bessel van der Kolk')
        self.assertEqual(data['isbn'], '9780143127741')  # prefers ISBN-13
        self.assertEqual(data['year_published'], 2014)
        self.assertEqual(data['page_count'], 464)
        self.assertEqual(data['average_rating'], 4.5)
        self.assertEqual(data['ratings_count'], 1200)

    def test_handles_missing_fields(self):
        data = normalize_volume({'id': 'x', 'volumeInfo': {}})
        self.assertEqual(data['title'], '')
        self.assertEqual(data['isbn'], '')
        self.assertIsNone(data['year_published'])
        self.assertIsNone(data['average_rating'])


class ResolveCoverTests(SimpleTestCase):
    def test_prefers_open_library_when_cover_exists(self):
        volume = normalize_volume(SAMPLE_VOLUME)
        url, source = resolve_cover(volume, open_library=_FakeOpenLibrary(has=True), policy='auto')
        self.assertEqual(source, 'openlibrary')
        self.assertIn('9780143127741-L.jpg', url)

    def test_auto_falls_back_to_google_thumbnail(self):
        volume = normalize_volume(SAMPLE_VOLUME)
        url, source = resolve_cover(volume, open_library=_FakeOpenLibrary(has=False), policy='auto')
        self.assertEqual(source, 'google')
        self.assertTrue(url.startswith('https://'))
        self.assertNotIn('edge=curl', url)

    def test_openlibrary_only_returns_nothing_without_cover(self):
        volume = normalize_volume(SAMPLE_VOLUME)
        url, source = resolve_cover(volume, open_library=_FakeOpenLibrary(has=False), policy='openlibrary_only')
        self.assertEqual((url, source), ('', ''))

    def test_upgrade_thumbnail(self):
        upgraded = _upgrade_google_thumbnail('http://x/y?zoom=1&edge=curl')
        self.assertEqual(upgraded, 'https://x/y?zoom=1')
