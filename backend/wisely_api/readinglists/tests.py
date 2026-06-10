from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from books.models import Book
from clinicians.models import Clinician
from readinglists.models import ReadingList, ReadingListItem

User = get_user_model()


def _clinician(username):
    user = User.objects.create_user(
        username=username, password="x", user_type="clinician", first_name="Dr", last_name=username
    )
    return Clinician.objects.create(user=user, bio="b")


class ReadingListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.clinician = _clinician("clin_rl")
        cls.other = _clinician("other_rl")
        cls.book = Book.objects.create(title="Calm Mind", author="Jane")

    def test_create_list(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(
            "/api/reading-lists/",
            {"title": "Anxiety starter", "description": "d", "purpose": "Tools for panic"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["share_token"])  # auto-generated
        self.assertEqual(res.data["purpose"], "Tools for panic")
        self.assertTrue(ReadingList.objects.filter(clinician=self.clinician, title="Anxiety starter").exists())

    def test_non_clinician_cannot_create(self):
        user = User.objects.create_user(username="plain", password="x")
        self.client.force_authenticate(user)
        res = self.client.post("/api/reading-lists/", {"title": "x"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_add_and_remove_book(self):
        rl = ReadingList.objects.create(clinician=self.clinician, title="L")
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(f"/api/reading-lists/{rl.id}/add-book/", {"book": self.book.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["book_count"], 1)
        # adding the same book again is a no-op
        res2 = self.client.post(f"/api/reading-lists/{rl.id}/add-book/", {"book": self.book.id}, format="json")
        self.assertEqual(res2.data["book_count"], 1)
        # remove
        res3 = self.client.post(f"/api/reading-lists/{rl.id}/remove-book/", {"book": self.book.id}, format="json")
        self.assertEqual(res3.data["book_count"], 0)

    def test_list_scoped_to_owner(self):
        ReadingList.objects.create(clinician=self.clinician, title="mine")
        ReadingList.objects.create(clinician=self.other, title="theirs")
        self.client.force_authenticate(self.clinician.user)
        res = self.client.get("/api/reading-lists/")
        self.assertEqual({r["title"] for r in res.data["results"]}, {"mine"})

    def test_cannot_edit_others_list(self):
        rl = ReadingList.objects.create(clinician=self.other, title="theirs")
        self.client.force_authenticate(self.clinician.user)
        res = self.client.patch(f"/api/reading-lists/{rl.id}/", {"title": "hacked"}, format="json")
        self.assertEqual(res.status_code, 404)  # scoped queryset hides it


class SharedReadingListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.clinician = _clinician("clin_share")
        cls.book = Book.objects.create(title="Calm Mind", author="Jane", isbn="9780143127741", isbn_10="0143127748")
        cls.rl = ReadingList.objects.create(
            clinician=cls.clinician, title="Anxiety", description="d", purpose="Tools for panic"
        )
        ReadingListItem.objects.create(reading_list=cls.rl, book=cls.book, position=1)

    def test_public_view_no_auth(self):
        res = self.client.get(f"/api/shared-lists/{self.rl.share_token}/")  # anonymous
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Anxiety")
        self.assertEqual(res.data["purpose"], "Tools for panic")  # patient sees the intent
        self.assertEqual(len(res.data["items"]), 1)
        self.assertEqual(res.data["items"][0]["book"]["title"], "Calm Mind")
        self.assertIn("buy_links", res.data["items"][0]["book"])  # patient can buy
        self.assertEqual(res.data["clinician_user_id"], self.clinician.user_id)  # viewer can follow

    def test_unshared_list_is_404(self):
        self.rl.is_shared = False
        self.rl.save()
        res = self.client.get(f"/api/shared-lists/{self.rl.share_token}/")
        self.assertEqual(res.status_code, 404)

    def test_bad_token_is_404(self):
        self.assertEqual(self.client.get("/api/shared-lists/nope/").status_code, 404)
