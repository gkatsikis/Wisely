from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from clinicians.models import Clinician
from seekers.models import Seeker

User = get_user_model()


class UserDetailsRoleTests(APITestCase):
    def _me(self, user):
        self.client.force_authenticate(user)
        return self.client.get("/api/auth/user/")

    def test_plain_user_has_no_roles(self):
        res = self._me(User.objects.create_user(username="u1", password="x"))
        self.assertFalse(res.data["is_clinician"])
        self.assertFalse(res.data["is_seeker"])
        self.assertFalse(res.data["is_staff"])

    def test_clinician_role(self):
        user = User.objects.create_user(username="c1", password="x")
        Clinician.objects.create(user=user, bio="b")
        res = self._me(user)
        self.assertTrue(res.data["is_clinician"])
        self.assertFalse(res.data["is_seeker"])

    def test_seeker_role(self):
        user = User.objects.create_user(username="s1", password="x")
        Seeker.objects.create(user=user)
        res = self._me(user)
        self.assertTrue(res.data["is_seeker"])
        self.assertFalse(res.data["is_clinician"])

    def test_user_can_be_both(self):
        user = User.objects.create_user(username="b1", password="x")
        Clinician.objects.create(user=user, bio="b")
        Seeker.objects.create(user=user)
        res = self._me(user)
        self.assertTrue(res.data["is_clinician"])
        self.assertTrue(res.data["is_seeker"])

    def test_is_staff_is_read_only(self):
        user = User.objects.create_user(username="st1", password="x")
        self.client.force_authenticate(user)
        self.client.patch("/api/auth/user/", {"is_staff": True}, format="json")
        user.refresh_from_db()
        self.assertFalse(user.is_staff)  # cannot self-escalate

    def test_user_type_set_on_seeker_profile_creation(self):
        user = User.objects.create_user(username="ut1", password="x")
        self.client.force_authenticate(user)
        self.client.get("/api/seekers/me/")  # lazily creates the seeker profile
        user.refresh_from_db()
        self.assertEqual(user.user_type, "seeker")

    def test_user_type_set_on_clinician_profile_creation(self):
        user = User.objects.create_user(username="ut2", password="x")
        self.client.force_authenticate(user)
        self.client.post("/api/clinicians/me/", {"bio": "hi"}, format="json")
        user.refresh_from_db()
        self.assertEqual(user.user_type, "clinician")
