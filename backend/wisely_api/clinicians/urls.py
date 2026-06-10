from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    ClinicianProfileView,
    ClinicianVerifyView,
    ClinicianViewSet,
    LicenseTypeListView,
    MyLicenseViewSet,
    MySpecialtyViewSet,
)

app_name = "clinicians"

# The current clinician's own specialties/licenses, under /me/.
me_router = SimpleRouter()
me_router.register("specialties", MySpecialtyViewSet, basename="my-specialty")
me_router.register("licenses", MyLicenseViewSet, basename="my-license")

# Public directory at the root (matches numeric ids).
directory_router = SimpleRouter()
directory_router.register("", ClinicianViewSet, basename="clinician")

# Order matters: the literal /me/ and /license-types/ paths must precede the
# directory's catch-all /{id}/ route.
urlpatterns = [
    path("me/", ClinicianProfileView.as_view(), name="me"),
    path("me/verify/", ClinicianVerifyView.as_view(), name="verify"),
    path("me/", include(me_router.urls)),
    path("license-types/", LicenseTypeListView.as_view(), name="license-types"),
    *directory_router.urls,
]
