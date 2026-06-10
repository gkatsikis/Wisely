from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from books.models import Book, Review
from clinicians.models import Clinician, ClinicianLicense, ClinicianSpecialty, License
from clinicians.npi import verify_npi
from core.models import Category

User = get_user_model()


class ClinicianDirectoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.anxiety = Category.objects.create(name="Anxiety")
        cls.trauma = Category.objects.create(name="Trauma")
        cls.lcsw = License.objects.get_or_create(license_type="lcsw")[0]  # seeded by migration

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


class ClinicianSelfProfileTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="newclin", password="x")

    def test_get_404_if_not_clinician(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/clinicians/me/").status_code, 404)

    def test_create_profile(self):
        self.client.force_authenticate(self.user)
        res = self.client.post("/api/clinicians/me/", {"bio": "I help with anxiety."}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Clinician.objects.filter(user=self.user).exists())
        self.assertTrue(res.data["is_active"])

    def test_create_requires_bio(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/clinicians/me/", {}, format="json").status_code, 400)

    def test_cannot_create_twice(self):
        Clinician.objects.create(user=self.user, bio="x")
        self.client.force_authenticate(self.user)
        res = self.client.post("/api/clinicians/me/", {"bio": "y"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_update_profile(self):
        Clinician.objects.create(user=self.user, bio="old")
        self.client.force_authenticate(self.user)
        res = self.client.patch(
            "/api/clinicians/me/",
            {"bio": "new", "has_openings": True, "video_bio_url": "https://youtu.be/x"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        clinician = Clinician.objects.get(user=self.user)
        self.assertEqual(clinician.bio, "new")
        self.assertTrue(clinician.has_openings)

    def test_is_active_is_read_only(self):
        Clinician.objects.create(user=self.user, bio="x", is_active=True)
        self.client.force_authenticate(self.user)
        self.client.patch("/api/clinicians/me/", {"is_active": False}, format="json")
        self.assertTrue(Clinician.objects.get(user=self.user).is_active)

    def test_requires_auth(self):
        self.assertIn(self.client.get("/api/clinicians/me/").status_code, (401, 403))


class ClinicianSpecialtyMgmtTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(username="clin_sp", password="x", user_type="clinician")
        cls.clinician = Clinician.objects.create(user=user, bio="bio")
        cls.category = Category.objects.create(name="Anxiety")
        cls.other = User.objects.create_user(username="nobody", password="x")

    def test_add_specialty(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post("/api/clinicians/me/specialties/", {"category": self.category.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(
            ClinicianSpecialty.objects.filter(clinician=self.clinician, category=self.category).exists()
        )

    def test_duplicate_specialty_rejected(self):
        ClinicianSpecialty.objects.create(clinician=self.clinician, category=self.category)
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post("/api/clinicians/me/specialties/", {"category": self.category.id}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_list_own_specialties(self):
        ClinicianSpecialty.objects.create(clinician=self.clinician, category=self.category)
        self.client.force_authenticate(self.clinician.user)
        res = self.client.get("/api/clinicians/me/specialties/")
        self.assertEqual(len(res.data["results"]), 1)

    def test_delete_specialty(self):
        specialty = ClinicianSpecialty.objects.create(clinician=self.clinician, category=self.category)
        self.client.force_authenticate(self.clinician.user)
        res = self.client.delete(f"/api/clinicians/me/specialties/{specialty.id}/")
        self.assertEqual(res.status_code, 204)

    def test_non_clinician_forbidden(self):
        self.client.force_authenticate(self.other)
        res = self.client.post("/api/clinicians/me/specialties/", {"category": self.category.id}, format="json")
        self.assertEqual(res.status_code, 403)


class ClinicianLicenseMgmtTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(username="clin_lic", password="x", user_type="clinician")
        cls.clinician = Clinician.objects.create(user=user, bio="bio")
        cls.lcsw = License.objects.get(license_type="lcsw")  # seeded by migration

    def test_add_license_is_unverified(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(
            "/api/clinicians/me/licenses/",
            {"license": self.lcsw.id, "license_number": "ABC123", "issued_state": "CA"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["is_verified"])

    def test_cannot_self_verify(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post(
            "/api/clinicians/me/licenses/",
            {"license": self.lcsw.id, "license_number": "ABC", "issued_state": "CA", "is_verified": True},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["is_verified"])  # read-only — ignored

    def test_edit_resets_verification(self):
        lic = ClinicianLicense.objects.create(
            clinician=self.clinician, license=self.lcsw, license_number="OLD",
            issued_state="CA", is_verified=True,
        )
        self.client.force_authenticate(self.clinician.user)
        res = self.client.patch(
            f"/api/clinicians/me/licenses/{lic.id}/", {"license_number": "NEW"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        lic.refresh_from_db()
        self.assertEqual(lic.license_number, "NEW")
        self.assertFalse(lic.is_verified)  # editing invalidates verification

    def test_license_types_endpoint(self):
        res = self.client.get("/api/clinicians/license-types/")
        types = {row["license_type"] for row in res.data}
        self.assertIn("lcsw", types)
        self.assertGreaterEqual(len(res.data), 9)


class _FakeNPPESSession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, params=None, timeout=None):
        response = MagicMock()
        response.json.return_value = self.payload
        response.raise_for_status.return_value = None
        return response


def _nppes(first, last, status="A"):
    return _FakeNPPESSession({"results": [{"basic": {"first_name": first, "last_name": last, "status": status}}]})


class NPIServiceTests(SimpleTestCase):
    def test_active_name_match_verified(self):
        ok, _ = verify_npi("1234567890", "Jane", "Smith", session=_nppes("Jane", "Smith"))
        self.assertTrue(ok)

    def test_inactive_not_verified(self):
        ok, _ = verify_npi("1234567890", "Jane", "Smith", session=_nppes("Jane", "Smith", status="I"))
        self.assertFalse(ok)

    def test_name_mismatch_not_verified(self):
        ok, _ = verify_npi("1234567890", "Jane", "Smith", session=_nppes("John", "Doe"))
        self.assertFalse(ok)

    def test_not_found_not_verified(self):
        ok, _ = verify_npi("1234567890", "Jane", "Smith", session=_FakeNPPESSession({"results": []}))
        self.assertFalse(ok)


class ClinicianVerificationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user(
            username="vc", password="x", first_name="Jane", last_name="Smith", user_type="clinician"
        )
        cls.clinician = Clinician.objects.create(user=user, bio="b")

    @patch("clinicians.views.verify_npi")
    def test_verify_with_matching_npi(self, mock_verify):
        mock_verify.return_value = (True, {"status": "A"})
        self.clinician.npi = "1234567890"
        self.clinician.save()
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post("/api/clinicians/me/verify/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "verified")
        self.clinician.refresh_from_db()
        self.assertTrue(self.clinician.is_verified)
        self.assertIsNotNone(self.clinician.verified_at)

    @patch("clinicians.views.verify_npi")
    def test_mismatched_npi_queues_review(self, mock_verify):
        mock_verify.return_value = (False, {"status": "A", "name_matches": False})
        self.clinician.npi = "1234567890"
        self.clinician.save()
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post("/api/clinicians/me/verify/")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["status"], "pending_review")
        self.clinician.refresh_from_db()
        self.assertFalse(self.clinician.is_verified)
        self.assertTrue(self.clinician.verification_requests.filter(reason="npi_mismatch").exists())

    def test_no_npi_queues_review(self):
        self.client.force_authenticate(self.clinician.user)
        res = self.client.post("/api/clinicians/me/verify/")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["reason"], "no_npi")
        self.assertTrue(self.clinician.verification_requests.filter(reason="no_npi").exists())

    def test_is_verified_read_only_npi_writable(self):
        self.client.force_authenticate(self.clinician.user)
        self.client.patch("/api/clinicians/me/", {"is_verified": True, "npi": "1234567890"}, format="json")
        self.clinician.refresh_from_db()
        self.assertFalse(self.clinician.is_verified)  # cannot self-verify
        self.assertEqual(self.clinician.npi, "1234567890")  # npi is settable

    def test_verified_badge_in_directory(self):
        self.clinician.is_verified = True
        self.clinician.save()
        res = self.client.get(f"/api/clinicians/{self.clinician.id}/")
        self.assertTrue(res.data["is_verified"])
