from rest_framework import generics, permissions

from .models import Seeker
from .serializers import SeekerProfileSerializer


class SeekerProfileView(generics.RetrieveUpdateAPIView):
    """The current user's own seeker profile (a singleton, created on first access).

    - GET   /api/seekers/me/    your profile
    - PATCH /api/seekers/me/    update birthdate, state, interests, profile_image

    Name/email are edited via /api/auth/user/; saved books and following have their own
    endpoints under /api/engagement/.
    """

    serializer_class = SeekerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        seeker, _ = Seeker.objects.get_or_create(user=self.request.user)
        return seeker
