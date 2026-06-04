from rest_framework import serializers

from books.models import Review

from .models import Clinician, ClinicianLicense, ClinicianSpecialty


def _display_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


class SpecialtySerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = ClinicianSpecialty
        fields = ["id", "category", "description"]


class LicenseSerializer(serializers.ModelSerializer):
    # NOTE: license_number is deliberately NOT exposed in the public directory.
    license_type = serializers.CharField(source="license.get_license_type_display", read_only=True)
    state = serializers.CharField(source="get_issued_state_display", read_only=True)

    class Meta:
        model = ClinicianLicense
        fields = ["id", "license_type", "issued_state", "state", "is_verified", "expiration_date"]


class ClinicianReviewSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_cover = serializers.CharField(source="book.cover", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "book_id", "book_title", "book_cover", "rating", "content", "created_at"]


class ClinicianListSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)  # the user to follow
    name = serializers.SerializerMethodField()
    specialties = serializers.SerializerMethodField()
    states = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Clinician
        fields = [
            "id", "user_id", "name", "has_openings", "profile_image",
            "specialties", "states", "review_count",
        ]

    def get_name(self, obj):
        return _display_name(obj.user)

    def get_specialties(self, obj):
        return [s.category.name for s in obj.specialties.all()]

    def get_states(self, obj):
        return sorted({lic.issued_state for lic in obj.licenses.all()})

    def get_review_count(self, obj):
        # Uses the viewset annotation when present to avoid a per-row COUNT.
        count = getattr(obj, "_review_count", None)
        return count if count is not None else obj.reviews.count()


class ClinicianDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)  # the user to follow
    name = serializers.SerializerMethodField()
    specialties = SpecialtySerializer(many=True, read_only=True)
    licenses = LicenseSerializer(many=True, read_only=True)
    reviews = ClinicianReviewSerializer(many=True, read_only=True)
    follower_count = serializers.SerializerMethodField()

    class Meta:
        model = Clinician
        fields = [
            "id", "user_id", "name", "bio", "video_bio_url", "has_openings", "is_active",
            "profile_image", "contact_email", "contact_phone",
            "specialties", "licenses", "reviews", "follower_count",
        ]

    def get_name(self, obj):
        return _display_name(obj.user)

    def get_follower_count(self, obj):
        return obj.user.followers.count()
