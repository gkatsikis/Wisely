from rest_framework.routers import SimpleRouter

from .views import ReviewViewSet

app_name = "reviews"

router = SimpleRouter()
router.register("", ReviewViewSet, basename="review")

urlpatterns = router.urls
