from rest_framework import serializers

from books.models import Review

from .models import Clinician, ClinicianLicense, ClinicianSpecialty, License


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
            "id", "user_id", "name", "is_verified", "has_openings", "profile_image",
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
            "id", "user_id", "name", "is_verified", "bio", "video_bio_url", "has_openings", "is_active",
            "profile_image", "contact_email", "contact_phone",
            "specialties", "licenses", "reviews", "follower_count",
        ]

    def get_name(self, obj):
        return _display_name(obj.user)

    def get_follower_count(self, obj):
        return obj.user.followers.count()


class ClinicianSelfSerializer(serializers.ModelSerializer):
    """A clinician's own editable profile. Specialties/licenses are read-only here — manage
    them via /api/clinicians/me/specialties/ and /licenses/."""

    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    specialties = SpecialtySerializer(many=True, read_only=True)
    licenses = LicenseSerializer(many=True, read_only=True)
    follower_count = serializers.SerializerMethodField()

    class Meta:
        model = Clinician
        fields = [
            "id", "user_id", "username", "email", "first_name", "last_name",
            "bio", "video_bio_url", "has_openings", "is_active",
            "contact_email", "contact_phone", "profile_image", "npi",
            "is_verified", "verified_at",
            "specialties", "licenses", "follower_count", "last_active",
        ]
        read_only_fields = ["is_active", "last_active", "is_verified", "verified_at"]

    def get_follower_count(self, obj):
        return obj.user.followers.count()


class MySpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicianSpecialty
        fields = ["id", "category", "description"]

    def validate(self, attrs):
        if self.instance is None:
            clinician = self.context["request"].user.clinician_profile
            if ClinicianSpecialty.objects.filter(clinician=clinician, category=attrs["category"]).exists():
                raise serializers.ValidationError("You already have this specialty.")
        return attrs


class MyLicenseSerializer(serializers.ModelSerializer):
    license_type = serializers.CharField(source="license.get_license_type_display", read_only=True)

    class Meta:
        model = ClinicianLicense
        fields = [
            "id", "license", "license_type", "license_number",
            "issued_state", "issued_date", "expiration_date", "is_verified",
        ]
        read_only_fields = ["is_verified"]  # verification is admin-controlled

    def validate(self, attrs):
        if self.instance is None:
            clinician = self.context["request"].user.clinician_profile
            if ClinicianLicense.objects.filter(
                clinician=clinician,
                license=attrs.get("license"),
                issued_state=attrs.get("issued_state"),
            ).exists():
                raise serializers.ValidationError("You already have this license for this state.")
        return attrs


class LicenseTypeSerializer(serializers.ModelSerializer):
    """A license type for the 'add a license' picker."""

    display = serializers.CharField(source="get_license_type_display", read_only=True)
    description = serializers.CharField(read_only=True)   # model property
    requirements = serializers.CharField(read_only=True)  # model property

    class Meta:
        model = License
        fields = ["id", "license_type", "display", "description", "requirements"]
