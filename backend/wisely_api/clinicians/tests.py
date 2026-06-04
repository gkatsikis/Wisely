from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from books.models import Book, Review
from clinicians.models import Clinician, ClinicianLicense, ClinicianSpecialty, License
from core.models import Category

User = get_user_model()


class ClinicianDirectoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.anxiety = Category.objects.create(name="Anxiety")
        cls.trauma = Category.objects.create(name="Trauma")
        cls.lcsw = License.objects.create(license_type="lcsw")

        # Clinician A: CA, Anxiety, has openings, 1 review
        ua = User.objects.create_user(
            username="dr_a", password="x", first_name="Ada", last_name="Adams", user_type="clinician"
        )
        cls.a = Clinician.objects.create(user=ua, bio="CBT for anxiety", has_openings=True)
        ClinicianSpecialty.objects.create(clinician=cls.a, category=cls.anxiety)
        ClinicianLicense.objects.create(
            clinician=cls.a, license=cls.lcsw, license_number="SECRET-A", issued_state="CA", is_verified=True
        )
        book = Book.objects.create(title="The Body Keeps the Score")
        Review.objects.create(book=book, clinician=cls.a, rating=5, content="Essential.")

        # Clinician B: NY, Trauma, no openings
        ub = User.objects.create_user(
            username="dr_b", password="x", first_name="Ben", last_name="Brown", user_type="clinician"
        )
        cls.b = Clinician.objects.create(user=ub, bio="Trauma specialist", has_openings=False)
        ClinicianSpecialty.objects.create(clinician=cls.b, category=cls.trauma)
        ClinicianLicense.objects.create(
            clinician=cls.b, license=cls.lcsw, license_number="SECRET-B", issued_state="NY", is_verified=False
        )

        # Clinician C: inactive — must never appear
        uc = User.objects.create_user(username="dr_c", password="x", user_type="clinician")
        cls.c = Clinician.objects.create(user=uc, bio="inactive", is_active=False)

    def _names(self, res):
        return {row["name"] for row in res.data["results"]}

    def test_list_returns_active_only(self):
        res = self.client.get("/api/clinicians/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._names(res), {"Ada Adams", "Ben Brown"})

    def test_filter_by_state_case_insensitive(self):
        res = self.client.get("/api/clinicians/?state=ca")
        self.assertEqual(self._names(res), {"Ada Adams"})

    def test_filter_by_specialty_name(self):
        res = self.client.get("/api/clinicians/?specialty=Trauma")
        self.assertEqual(self._names(res), {"Ben Brown"})

    def test_filter_by_specialty_id(self):
        res = self.client.get(f"/api/clinicians/?specialty={self.anxiety.id}")
        self.assertEqual(self._names(res), {"Ada Adams"})

    def test_has_openings_filter(self):
        res = self.client.get("/api/clinicians/?has_openings=true")
        self.assertEqual(self._names(res), {"Ada Adams"})

    def test_search_q_matches_bio(self):
        res = self.client.get("/api/clinicians/?q=trauma")
        self.assertEqual(self._names(res), {"Ben Brown"})

    def test_list_summary_fields(self):
        row = self.client.get("/api/clinicians/?state=CA").data["results"][0]
        self.assertEqual(row["review_count"], 1)
        self.assertEqual(row["states"], ["CA"])
        self.assertEqual(row["specialties"], ["Anxiety"])

    def test_detail_shape_and_license_privacy(self):
        res = self.client.get(f"/api/clinicians/{self.a.id}/")
        self.assertEqual(res.status_code, 200)
        data = res.data
        self.assertEqual(data["name"], "Ada Adams")
        self.assertEqual(data["bio"], "CBT for anxiety")
        self.assertEqual(len(data["reviews"]), 1)
        self.assertEqual(data["reviews"][0]["book_title"], "The Body Keeps the Score")
        self.assertEqual(len(data["licenses"]), 1)
        self.assertNotIn("license_number", data["licenses"][0])  # private
        self.assertNotIn("SECRET", str(data))  # number must not leak anywhere

    def test_inactive_clinician_is_404(self):
        res = self.client.get(f"/api/clinicians/{self.c.id}/")
        self.assertEqual(res.status_code, 404)

    def test_categories_endpoint(self):
        res = self.client.get("/api/categories/")
        names = {c["name"] for c in res.data}
        self.assertTrue({"Anxiety", "Trauma"}.issubset(names))
