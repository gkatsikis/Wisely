from django.db.models import Count, Q
from rest_framework import viewsets

from .models import Clinician
from .serializers import ClinicianDetailSerializer, ClinicianListSerializer

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
