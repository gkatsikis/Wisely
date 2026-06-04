import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from books.models import Book
from clinicians.models import Clinician
from core.models import Category
from engagement.models import Follow, SavedBook
from seekers.models import Seeker

User = get_user_model()


def _tiny_png():
    buf = BytesIO()
    Image.new("RGB", (1, 1)).save(buf, "PNG")
    buf.seek(0)
    return SimpleUploadedFile("p.png", buf.read(), content_type="image/png")


class SeekerProfileTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="m1", password="x", user_type="seeker")
        cls.anxiety = Category.objects.create(name="Anxiety")

    def test_get_creates_profile_lazily(self):
        self.assertFalse(Seeker.objects.filter(user=self.user).exists())
        self.client.force_authenticate(self.user)
        res = self.client.get("/api/seekers/me/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Seeker.objects.filter(user=self.user).exists())
        self.assertEqual(res.data["username"], "m1")
        self.assertIn("profile_image", res.data)

    def test_update_fields_and_interests(self):
        self.client.force_authenticate(self.user)
        res = self.client.patch(
            "/api/seekers/me/",
            {"birthdate": "1990-05-01", "state": "CA", "interests": [self.anxiety.id]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        seeker = Seeker.objects.get(user=self.user)
        self.assertEqual(str(seeker.birthdate), "1990-05-01")
        self.assertEqual(seeker.state, "CA")
        self.assertEqual(list(seeker.interests.values_list("name", flat=True)), ["Anxiety"])

    def test_counts(self):
        seeker = Seeker.objects.create(user=self.user)
        clin_user = User.objects.create_user(username="clin", password="x", user_type="clinician")
        Clinician.objects.create(user=clin_user, bio="b")
        book = Book.objects.create(title="B")
        SavedBook.objects.create(seeker=seeker, book=book)
        Follow.objects.create(follower=self.user, followee=clin_user)
        self.client.force_authenticate(self.user)
        res = self.client.get("/api/seekers/me/")
        self.assertEqual(res.data["saved_books_count"], 1)
        self.assertEqual(res.data["following_count"], 1)

    def test_requires_auth(self):
        res = self.client.get("/api/seekers/me/")
        self.assertIn(res.status_code, (401, 403))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_upload_profile_image(self):
        self.client.force_authenticate(self.user)
        res = self.client.patch(
            "/api/seekers/me/", {"profile_image": _tiny_png()}, format="multipart"
        )
        self.assertEqual(res.status_code, 200)
        seeker = Seeker.objects.get(user=self.user)
        self.assertTrue(seeker.profile_image.name)
