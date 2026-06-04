from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from books.models import Book, Review
from clinicians.models import Clinician
from engagement.models import Event, Follow, SavedBook
from seekers.models import Seeker

User = get_user_model()


def _seeker(username):
    user = User.objects.create_user(username=username, password="x", user_type="seeker")
    return Seeker.objects.create(user=user)


def _clinician(username):
    user = User.objects.create_user(
        username=username, password="x", user_type="clinician", first_name="Dr", last_name=username
    )
    return Clinician.objects.create(user=user, bio="bio")


class FollowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seeker = _seeker("seeker_f")
        cls.clinician = _clinician("clin_f")
        cls.book = Book.objects.create(title="The Body Keeps the Score")
        cls.review = Review.objects.create(book=cls.book, clinician=cls.clinician, rating=5, content="x")

    def test_follow(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post("/api/engagement/follows/", {"followee": self.clinician.user_id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Follow.objects.filter(follower=self.seeker.user, followee=self.clinician.user).exists())

    def test_cannot_follow_self(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post("/api/engagement/follows/", {"followee": self.seeker.user_id}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_duplicate_follow_rejected(self):
        Follow.objects.create(follower=self.seeker.user, followee=self.clinician.user)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post("/api/engagement/follows/", {"followee": self.clinician.user_id}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_unfollow_by_followee_id(self):
        Follow.objects.create(follower=self.seeker.user, followee=self.clinician.user)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.delete(f"/api/engagement/follows/{self.clinician.user_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Follow.objects.filter(follower=self.seeker.user, followee=self.clinician.user).exists())

    def test_list_my_following(self):
        Follow.objects.create(follower=self.seeker.user, followee=self.clinician.user)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.get("/api/engagement/follows/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["followee"], self.clinician.user_id)

    def test_anonymous_cannot_follow(self):
        res = self.client.post("/api/engagement/follows/", {"followee": self.clinician.user_id}, format="json")
        self.assertIn(res.status_code, (401, 403))

    def test_follow_auto_logs_event_with_attribution(self):
        self.client.force_authenticate(self.seeker.user)
        self.client.post(
            "/api/engagement/follows/",
            {"followee": self.clinician.user_id, "source_review": self.review.id},
            format="json",
        )
        event = Event.objects.get(event_type="clinician_followed")
        self.assertEqual(event.actor, self.seeker.user)
        self.assertEqual(event.clinician, self.clinician)
        self.assertEqual(event.source_review, self.review)  # attribution carried through

    def test_unfollow_auto_logs_event(self):
        Follow.objects.create(follower=self.seeker.user, followee=self.clinician.user)
        self.client.force_authenticate(self.seeker.user)
        self.client.delete(f"/api/engagement/follows/{self.clinician.user_id}/")
        self.assertTrue(
            Event.objects.filter(event_type="clinician_unfollowed", clinician=self.clinician).exists()
        )


class SavedBookTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seeker = _seeker("seeker_s")
        cls.clinician = _clinician("clin_s")
        cls.book = Book.objects.create(title="Book A")
        cls.book2 = Book.objects.create(title="Book B")
        cls.review = Review.objects.create(book=cls.book, clinician=cls.clinician, rating=5, content="x")

    def test_save_book(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post("/api/engagement/saved-books/", {"book": self.book.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(SavedBook.objects.filter(seeker=self.seeker, book=self.book).exists())

    def test_save_with_via_review(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post(
            "/api/engagement/saved-books/", {"book": self.book.id, "via_review": self.review.id}, format="json"
        )
        self.assertEqual(res.status_code, 201)

    def test_via_review_must_match_book(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post(
            "/api/engagement/saved-books/", {"book": self.book2.id, "via_review": self.review.id}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_duplicate_save_rejected(self):
        SavedBook.objects.create(seeker=self.seeker, book=self.book)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post("/api/engagement/saved-books/", {"book": self.book.id}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_unsave_by_book_id(self):
        SavedBook.objects.create(seeker=self.seeker, book=self.book)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.delete(f"/api/engagement/saved-books/{self.book.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(SavedBook.objects.filter(seeker=self.seeker, book=self.book).exists())

    def test_non_seeker_cannot_save(self):
        self.client.force_authenticate(self.clinician.user)  # no seeker_profile
        res = self.client.post("/api/engagement/saved-books/", {"book": self.book.id}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_list_my_saves(self):
        SavedBook.objects.create(seeker=self.seeker, book=self.book)
        self.client.force_authenticate(self.seeker.user)
        res = self.client.get("/api/engagement/saved-books/")
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["book_title"], "Book A")

    def test_save_auto_logs_event_with_attribution(self):
        self.client.force_authenticate(self.seeker.user)
        self.client.post(
            "/api/engagement/saved-books/",
            {"book": self.book.id, "via_review": self.review.id},
            format="json",
        )
        event = Event.objects.get(event_type="book_saved")
        self.assertEqual(event.book, self.book)
        self.assertEqual(event.source_review, self.review)  # from via_review

    def test_unsave_auto_logs_event(self):
        SavedBook.objects.create(seeker=self.seeker, book=self.book)
        self.client.force_authenticate(self.seeker.user)
        self.client.delete(f"/api/engagement/saved-books/{self.book.id}/")
        self.assertTrue(Event.objects.filter(event_type="book_unsaved", book=self.book).exists())


class EventTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(title="Book A")
        cls.seeker = _seeker("seeker_e")

    def test_anonymous_event(self):
        res = self.client.post(
            "/api/engagement/events/",
            {"event_type": "book_viewed", "book": self.book.id, "session_id": "abc"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        event = Event.objects.get(id=res.data["id"])
        self.assertIsNone(event.actor)
        self.assertEqual(event.session_id, "abc")

    def test_authenticated_event_sets_actor(self):
        self.client.force_authenticate(self.seeker.user)
        res = self.client.post(
            "/api/engagement/events/", {"event_type": "book_saved", "book": self.book.id}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Event.objects.get(id=res.data["id"]).actor, self.seeker.user)

    def test_invalid_event_type_rejected(self):
        res = self.client.post("/api/engagement/events/", {"event_type": "nonsense"}, format="json")
        self.assertEqual(res.status_code, 400)
