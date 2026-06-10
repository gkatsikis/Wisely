from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class WiselyUserDetailsSerializer(UserDetailsSerializer):
    """Adds role info to /api/auth/user/ for role-based UI.

    `is_clinician` / `is_seeker` are derived from whether the user has the matching profile —
    always accurate, and a person can be both. `user_type` is a soft 'primary role' hint
    (what they signed up as / their first profile); `is_staff` flags admin/dev access. Roles
    can't be changed here (read-only) — they follow from profiles and Django permissions.
    """

    is_clinician = serializers.SerializerMethodField()
    is_seeker = serializers.SerializerMethodField()

    class Meta(UserDetailsSerializer.Meta):
        fields = (*UserDetailsSerializer.Meta.fields, "user_type", "is_staff", "is_clinician", "is_seeker")
        read_only_fields = (*UserDetailsSerializer.Meta.read_only_fields, "user_type", "is_staff")

    def get_is_clinician(self, obj):
        return hasattr(obj, "clinician_profile")

    def get_is_seeker(self, obj):
        return hasattr(obj, "seeker_profile")
