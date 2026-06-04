from rest_framework import mixins, permissions, viewsets

from core.permissions import IsSeeker

from .models import Follow, SavedBook
from .serializers import EventSerializer, FollowSerializer, SavedBookSerializer


class FollowViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                    mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """The current user's follow graph.

    - GET    /api/engagement/follows/                 users you follow
    - POST   /api/engagement/follows/   {followee}    follow a user
    - DELETE /api/engagement/follows/{followee_id}/   unfollow
    """

    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "followee_id"

    def get_queryset(self):
        return (
            Follow.objects.filter(follower=self.request.user)
            .select_related("followee")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)


class SavedBookViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """A seeker's bookmarked books.

    - GET    /api/engagement/saved-books/                    your saved books
    - POST   /api/engagement/saved-books/  {book, via_review?}   save a book
    - DELETE /api/engagement/saved-books/{book_id}/          unsave
    """

    serializer_class = SavedBookSerializer
    permission_classes = [IsSeeker]
    lookup_field = "book_id"

    def get_queryset(self):
        return (
            SavedBook.objects.filter(seeker=self.request.user.seeker_profile)
            .select_related("book")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user.seeker_profile)


class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Append-only clickstream ingestion. Accepts anonymous events (with a session_id).

    - POST /api/engagement/events/  {event_type, book?, clinician?, review?, source_review?,
                                      provider?, session_id?, metadata?}
    """

    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        serializer.save(actor=actor)
