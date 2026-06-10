from django.urls import reverse
from rest_framework import serializers

from books.models import Book
from books.services.affiliate import PROVIDERS, affiliate_url

from .models import ReadingList, ReadingListItem


class ListBookSerializer(serializers.ModelSerializer):
    """Compact book info for a reading-list item, including affiliate buy-links."""

    cover = serializers.CharField(read_only=True)
    buy_links = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "subtitle", "author", "cover", "buy_links"]

    def get_buy_links(self, obj):
        request = self.context.get("request")
        links = {}
        for provider in PROVIDERS:
            if not affiliate_url(obj, provider):
                continue
            path = reverse("books:book-buy", args=[obj.pk]) + f"?provider={provider}"
            links[provider] = request.build_absolute_uri(path) if request else path
        return links


class ReadingListItemSerializer(serializers.ModelSerializer):
    book = ListBookSerializer(read_only=True)

    class Meta:
        model = ReadingListItem
        fields = ["id", "book", "position"]


class ReadingListSerializer(serializers.ModelSerializer):
    """A clinician's own reading list (create/edit). Books are added/removed via the
    add-book / remove-book actions, not here."""

    items = ReadingListItemSerializer(many=True, read_only=True)
    book_count = serializers.SerializerMethodField()

    class Meta:
        model = ReadingList
        fields = [
            "id", "title", "description", "purpose", "is_shared", "share_token",
            "items", "book_count", "created_at", "updated_at",
        ]
        read_only_fields = ["share_token", "created_at", "updated_at"]

    def get_book_count(self, obj):
        return obj.items.count()


class SharedReadingListSerializer(serializers.ModelSerializer):
    """Public, read-only view of a shared list (no account needed). Exposes the clinician's
    ids so a signed-in viewer can follow them / open their profile — but no contact info."""

    items = ReadingListItemSerializer(many=True, read_only=True)
    clinician_id = serializers.IntegerField(read_only=True)
    clinician_user_id = serializers.IntegerField(source="clinician.user_id", read_only=True)
    clinician_name = serializers.SerializerMethodField()

    class Meta:
        model = ReadingList
        fields = [
            "title", "description", "purpose", "clinician_id", "clinician_user_id",
            "clinician_name", "items", "created_at",
        ]

    def get_clinician_name(self, obj):
        user = obj.clinician.user
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.username
