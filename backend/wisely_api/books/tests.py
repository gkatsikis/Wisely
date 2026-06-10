from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from books.models import Book, Review
from books.services.covers import _upgrade_google_thumbnail, resolve_cover
from books.services.google_books import normalize_volume
from clinicians.models import Clinician
from core.models import Category
from seekers.models import Seeker

User = get_user_model()

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


def _make_clinician(username, **user_kwargs):
    user = User.objects.create_user(username=username, password='x', user_type='clinician', **user_kwargs)
    return Clinician.objects.create(user=user, bio='bio')


class ReviewAuthoringTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title='The Body Keeps the Score')
        cls.book2 = Book.objects.create(title='Attached')
        cls.clinician = _make_clinician('dr_a', first_name='Ada', last_name='Adams')
        cls.other = _make_clinician('dr_b', first_name='Ben', last_name='Brown')
        cls.seeker_user = User.objects.create_user(username='seeker1', password='x', user_type='seeker')
        Seeker.objects.create(user=cls.seeker_user)

    def _review(self, clinician=None, book=None, rating=3):
        return Review.objects.create(
            book=book or self.book, clinician=clinician or self.clinician, rating=rating, content='x'
        )

    def test_clinician_can_create_review(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(
            '/api/reviews/', {'book': self.book.id, 'rating': 5, 'content': 'Essential.'}, format='json'
        )
        self.assertEqual(res.status_code, 201)
        review = Review.objects.get(id=res.data['id'])
        self.assertEqual(review.clinician, self.clinician)
        self.assertEqual(review.rating, 5)

    def test_clinician_taken_from_user_not_body(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(
            '/api/reviews/',
            {'book': self.book.id, 'rating': 4, 'content': 'x', 'clinician': self.other.id},
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Review.objects.get(id=res.data['id']).clinician, self.clinician)

    def test_seeker_cannot_create(self):
        self.client.force_authenticate(self.seeker_user)
        res = self.client.post('/api/reviews/', {'book': self.book.id, 'rating': 5, 'content': 'x'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_anonymous_cannot_create(self):
        res = self.client.post('/api/reviews/', {'book': self.book.id, 'rating': 5, 'content': 'x'}, format='json')
        self.assertIn(res.status_code, (401, 403))

    def test_duplicate_review_rejected(self):
        self.client.force_authenticate(self.clinician.user)
        self.client.post('/api/reviews/', {'book': self.book.id, 'rating': 5, 'content': 'first'}, format='json')
        res = self.client.post('/api/reviews/', {'book': self.book.id, 'rating': 3, 'content': 'again'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_rating_out_of_range(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post('/api/reviews/', {'book': self.book.id, 'rating': 6, 'content': 'x'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_update_own_review(self):
        review = self._review(rating=3)
        self.client.force_authenticate(self.clinician.user)
        res = self.client.patch(f'/api/reviews/{review.id}/', {'rating': 5}, format='json')
        self.assertEqual(res.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)

    def test_cannot_update_others_review(self):
        review = self._review()
        self.client.force_authenticate(self.other.user)
        res = self.client.patch(f'/api/reviews/{review.id}/', {'rating': 1}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_book_is_immutable_on_update(self):
        review = self._review()
        self.client.force_authenticate(self.clinician.user)
        res = self.client.patch(f'/api/reviews/{review.id}/', {'book': self.book2.id, 'rating': 4}, format='json')
        self.assertEqual(res.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.book, self.book)  # book change ignored

    def test_delete_own_review(self):
        review = self._review()
        self.client.force_authenticate(self.clinician.user)
        res = self.client.delete(f'/api/reviews/{review.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    def test_list_reviews_public_and_filtered_by_book(self):
        self._review(book=self.book, rating=5)
        self._review(book=self.book2, rating=4)
        res = self.client.get(f'/api/reviews/?book={self.book.id}')  # anonymous
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['book_title'], 'The Body Keeps the Score')

    def test_review_exposes_reviewer_verified_flag(self):
        self._review()
        res = self.client.get(f'/api/reviews/?book={self.book.id}')
        self.assertIn('is_verified', res.data['results'][0]['clinician'])


class BookCatalogFilterTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.anxiety = Category.objects.create(name='Anxiety')
        trauma = Category.objects.create(name='Trauma')
        cls.b1 = Book.objects.create(title='Calm Mind', author='Jane Doe')
        cls.b1.categories.add(cls.anxiety)
        cls.b2 = Book.objects.create(title='Healing Trauma', author='John Roe')
        cls.b2.categories.add(trauma)

    def _titles(self, res):
        return {row['title'] for row in res.data['results']}

    def test_filter_by_category_name(self):
        self.assertEqual(self._titles(self.client.get('/api/books/?category=Trauma')), {'Healing Trauma'})

    def test_filter_by_category_id(self):
        self.assertEqual(
            self._titles(self.client.get(f'/api/books/?category={self.anxiety.id}')), {'Calm Mind'}
        )

    def test_search_q_matches_title_and_author(self):
        self.assertEqual(self._titles(self.client.get('/api/books/?q=calm')), {'Calm Mind'})
        self.assertEqual(self._titles(self.client.get('/api/books/?q=roe')), {'Healing Trauma'})

    def test_list_returns_all(self):
        self.assertEqual(self._titles(self.client.get('/api/books/')), {'Calm Mind', 'Healing Trauma'})
