from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ReadingListViewSet, SharedReadingListView

app_name = "readinglists"

router = SimpleRouter()
router.register("reading-lists", ReadingListViewSet, basename="reading-list")

urlpatterns = [
    path("shared-lists/<str:token>/", SharedReadingListView.as_view(), name="shared-list"),
    *router.urls,
]
