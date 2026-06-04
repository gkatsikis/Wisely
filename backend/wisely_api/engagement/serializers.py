from rest_framework import serializers

from .models import Event, Follow, SavedBook


def _display_name(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.username


class FollowSerializer(serializers.ModelSerializer):
    followee_name = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = ["id", "followee", "followee_name", "created_at"]
        read_only_fields = ["created_at"]

    def get_followee_name(self, obj):
        return _display_name(obj.followee)

    def validate_followee(self, value):
        if value == self.context["request"].user:
            raise serializers.ValidationError("You cannot follow yourself.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            user = self.context["request"].user
            if Follow.objects.filter(follower=user, followee=attrs["followee"]).exists():
                raise serializers.ValidationError("You already follow this user.")
        return attrs


class SavedBookSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = SavedBook
        fields = ["id", "book", "book_title", "via_review", "created_at"]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        book = attrs.get("book")
        via_review = attrs.get("via_review")
        if via_review and via_review.book_id != book.id:
            raise serializers.ValidationError({"via_review": "Review must be for the same book."})
        if self.instance is None:
            seeker = self.context["request"].user.seeker_profile
            if SavedBook.objects.filter(seeker=seeker, book=book).exists():
                raise serializers.ValidationError("You have already saved this book.")
        return attrs


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id", "event_type", "session_id",
            "book", "clinician", "review", "source_review",
            "provider", "metadata", "created_at",
        ]
        read_only_fields = ["created_at"]
