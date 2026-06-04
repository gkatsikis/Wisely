from rest_framework import permissions


class IsClinicianOrReadOnly(permissions.BasePermission):
    """Read for anyone; write only for an authenticated user who has a clinician profile."""

    message = "Only clinicians can perform this action."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, "clinician_profile"))


class IsReviewAuthorOrReadOnly(permissions.BasePermission):
    """Object-level: read for anyone; write only by the clinician who wrote the review."""

    message = "You can only modify your own review."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.clinician.user_id == request.user.id


class IsSeeker(permissions.BasePermission):
    """Authenticated users who have a seeker profile (e.g. for their own saved books)."""

    message = "Only seekers can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, "seeker_profile"))
