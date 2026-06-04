from rest_framework import serializers

from core.models import Category

from .models import Seeker


class SeekerProfileSerializer(serializers.ModelSerializer):
    # User fields are read-only here — edit name/email via /api/auth/user/.
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    interests = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )
    saved_books_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = Seeker
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "birthdate", "state", "interests", "profile_image",
            "saved_books_count", "following_count",
        ]

    def get_saved_books_count(self, obj):
        return obj.saved_books.count()

    def get_following_count(self, obj):
        return obj.user.following.count()
