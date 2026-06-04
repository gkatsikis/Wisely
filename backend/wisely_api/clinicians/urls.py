from rest_framework.routers import SimpleRouter

from .views import ClinicianViewSet

app_name = "clinicians"

router = SimpleRouter()
router.register("", ClinicianViewSet, basename="clinician")

urlpatterns = router.urls
