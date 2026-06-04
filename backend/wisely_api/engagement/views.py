from rest_framework import mixins, permissions, viewsets

from core.permissions import IsSeeker

from .models import Event, Follow, SavedBook
from .serializers import EventSerializer, FollowSerializer, SavedBookSerializer
from .services import log_event


class FollowViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                    mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """The current user's follow graph.

    - GET    /api/engagement/follows/                 users you follow
    - POST   /api/engagement/follows/   {followee, source_review?}    follow a user
    - DELETE /api/engagement/follows/{followee_id}/   unfollow

    Following/unfollowing a clinician auto-logs a clinician_followed / clinician_unfollowed event.
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
        follow = serializer.save(follower=self.request.user)
        clinician = getattr(follow.followee, "clinician_profile", None)
        if clinician is not None:  # we only have a clinician-scoped follow event type
            log_event(self.request, Event.Type.CLINICIAN_FOLLOWED, clinician=clinician)

    def perform_destroy(self, instance):
        clinician = getattr(instance.followee, "clinician_profile", None)
        instance.delete()
        if clinician is not None:
            log_event(self.request, Event.Type.CLINICIAN_UNFOLLOWED, clinician=clinician)


class SavedBookViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """A seeker's bookmarked books.

    - GET    /api/engagement/saved-books/                    your saved books
    - POST   /api/engagement/saved-books/  {book, via_review?}   save a book
    - DELETE /api/engagement/saved-books/{book_id}/          unsave

    Saving/unsaving auto-logs a book_saved / book_unsaved event (attributed via via_review).
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
        saved = serializer.save(seeker=self.request.user.seeker_profile)
        # The review that drove the save (if any) is the attribution.
        log_event(self.request, Event.Type.BOOK_SAVED, book=saved.book, source_review=saved.via_review)

    def perform_destroy(self, instance):
        book = instance.book
        instance.delete()
        log_event(self.request, Event.Type.BOOK_UNSAVED, book=book)


class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Append-only clickstream ingestion for events only the client can see (views, clicks,
    searches). Accepts anonymous events (with a session_id).

    - POST /api/engagement/events/  {event_type, book?, clinician?, review?, source_review?,
                                      provider?, session_id?, metadata?}
    """

    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        serializer.save(actor=actor)
