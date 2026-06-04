from rest_framework.routers import SimpleRouter

from .views import EventViewSet, FollowViewSet, SavedBookViewSet

app_name = "engagement"

router = SimpleRouter()
router.register("follows", FollowViewSet, basename="follow")
router.register("saved-books", SavedBookViewSet, basename="saved-book")
router.register("events", EventViewSet, basename="event")

urlpatterns = router.urls
