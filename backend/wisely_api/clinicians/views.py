from django.db.models import Count, Q
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsClinician

from .models import (
    Clinician,
    ClinicianLicense,
    ClinicianSpecialty,
    License,
    ManualVerificationRequest,
)
from .npi import verify_npi
from .serializers import (
    ClinicianDetailSerializer,
    ClinicianListSerializer,
    ClinicianSelfSerializer,
    LicenseTypeSerializer,
    MyLicenseSerializer,
    MySpecialtySerializer,
)

TRUTHY = {"1", "true", "yes", "on"}


class ClinicianViewSet(viewsets.ReadOnlyModelViewSet):
    """Public directory of clinicians.

    - GET /api/clinicians/         list active clinicians (summary)
        filters: ?specialty=<id|name>  ?state=XX  ?has_openings=true  ?q=<name/bio>
    - GET /api/clinicians/{id}/    full profile (bio, video, specialties, licenses, reviews)
    """

    def get_queryset(self):
        qs = (
            Clinician.objects.filter(is_active=True)
            .select_related("user")
            .annotate(_review_count=Count("reviews", distinct=True))
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("specialties__category", "licenses__license", "reviews__book")
        else:
            qs = qs.prefetch_related("specialties__category", "licenses")

        params = self.request.query_params

        state = params.get("state")
        if state:
            qs = qs.filter(licenses__issued_state=state.upper())

        specialty = params.get("specialty")
        if specialty:
            if specialty.isdigit():
                qs = qs.filter(specialties__category_id=int(specialty))
            else:
                qs = qs.filter(specialties__category__name__iexact=specialty)

        if params.get("has_openings", "").lower() in TRUTHY:
            qs = qs.filter(has_openings=True)

        q = params.get("q")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(bio__icontains=q)
            )

        return qs.distinct().order_by("user__last_name", "user__first_name")

    def get_serializer_class(self):
        return ClinicianDetailSerializer if self.action == "retrieve" else ClinicianListSerializer


class ClinicianProfileView(generics.GenericAPIView, mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin):
    """The current user's own clinician profile.

    - GET   /api/clinicians/me/    your profile (404 if you aren't a clinician yet)
    - POST  /api/clinicians/me/    become a clinician (create your profile; bio required)
    - PATCH /api/clinicians/me/    update your profile
    """

    serializer_class = ClinicianSelfSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        clinician = getattr(self.request.user, "clinician_profile", None)
        if clinician is None:
            raise Http404("You don't have a clinician profile yet.")
        return clinician

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if getattr(request.user, "clinician_profile", None) is not None:
            return Response(
                {"detail": "You already have a clinician profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        if not request.user.user_type:
            request.user.user_type = "clinician"
            request.user.save(update_fields=["user_type"])
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MySpecialtyViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                         mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """The current clinician's specialties (list/add/edit/remove your own)."""

    serializer_class = MySpecialtySerializer
    permission_classes = [IsClinician]

    def get_queryset(self):
        return (
            ClinicianSpecialty.objects.filter(clinician=self.request.user.clinician_profile)
            .select_related("category")
            .order_by("category__name")
        )

    def perform_create(self, serializer):
        serializer.save(clinician=self.request.user.clinician_profile)


class MyLicenseViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                       mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """The current clinician's licenses. `is_verified` is admin-controlled and resets on edit."""

    serializer_class = MyLicenseSerializer
    permission_classes = [IsClinician]

    def get_queryset(self):
        return (
            ClinicianLicense.objects.filter(clinician=self.request.user.clinician_profile)
            .select_related("license")
            .order_by("license__license_type")
        )

    def perform_create(self, serializer):
        serializer.save(clinician=self.request.user.clinician_profile)

    def perform_update(self, serializer):
        # Editing license details invalidates any prior verification.
        serializer.save(is_verified=False)


class LicenseTypeListView(generics.ListAPIView):
    """The available license types (to populate the 'add a license' picker)."""

    queryset = License.objects.order_by("license_type")
    serializer_class = LicenseTypeSerializer
    pagination_class = None


class ClinicianVerifyView(APIView):
    """Request verification for the current clinician.

    POST /api/clinicians/me/verify/ — checks the clinician's NPI against the federal NPPES
    registry and, on an active + name match, awards the verified badge. With no NPI (or a
    mismatch / inactive NPI) it logs a ManualVerificationRequest for a human to resolve.
    """

    permission_classes = [IsClinician]

    def post(self, request):
        clinician = request.user.clinician_profile
        if clinician.is_verified:
            return Response({"status": "verified"})

        user = request.user
        reason, notes = "no_npi", ""
        if clinician.npi:
            verified, detail = verify_npi(clinician.npi, user.first_name, user.last_name)
            if verified:
                clinician.is_verified = True
                clinician.verified_at = timezone.now()
                clinician.save(update_fields=["is_verified", "verified_at"])
                return Response({"status": "verified", "detail": detail})
            reason = "npi_inactive" if detail.get("status") not in (None, "A") else "npi_mismatch"
            notes = str(detail)

        if not clinician.verification_requests.filter(resolved=False).exists():
            ManualVerificationRequest.objects.create(clinician=clinician, reason=reason, notes=notes)
        return Response({"status": "pending_review", "reason": reason}, status=status.HTTP_202_ACCEPTED)
