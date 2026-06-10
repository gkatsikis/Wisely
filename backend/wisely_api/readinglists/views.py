from django.db.models import Max
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from books.models import Book
from core.permissions import IsClinician

from .models import ReadingList, ReadingListItem
from .serializers import ReadingListSerializer, SharedReadingListSerializer


class ReadingListViewSet(viewsets.ModelViewSet):
    """A clinician's own reading lists (bibliotherapy).

    - CRUD at /api/reading-lists/
    - POST /api/reading-lists/{id}/add-book/     {book}
    - POST /api/reading-lists/{id}/remove-book/  {book}

    Share a list via its `share_token` -> /api/shared-lists/{token}/ (public, no account).
    """

    serializer_class = ReadingListSerializer
    permission_classes = [IsClinician]

    def get_queryset(self):
        return (
            ReadingList.objects.filter(clinician=self.request.user.clinician_profile)
            .prefetch_related("items__book")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(clinician=self.request.user.clinician_profile)

    def _list_response(self, reading_list, created=False):
        # Re-fetch so the (prefetched) items / book_count reflect the change just made.
        reading_list = self.get_queryset().get(pk=reading_list.pk)
        data = ReadingListSerializer(reading_list, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add-book")
    def add_book(self, request, pk=None):
        reading_list = self.get_object()
        book_id = request.data.get("book")
        if not book_id:
            return Response({"detail": "book is required."}, status=status.HTTP_400_BAD_REQUEST)
        book = get_object_or_404(Book, pk=book_id)
        _, created = ReadingListItem.objects.get_or_create(
            reading_list=reading_list,
            book=book,
            defaults={"position": (reading_list.items.aggregate(m=Max("position"))["m"] or 0) + 1},
        )
        return self._list_response(reading_list, created=created)

    @action(detail=True, methods=["post"], url_path="remove-book")
    def remove_book(self, request, pk=None):
        reading_list = self.get_object()
        ReadingListItem.objects.filter(
            reading_list=reading_list, book_id=request.data.get("book")
        ).delete()
        return self._list_response(reading_list)


class SharedReadingListView(generics.RetrieveAPIView):
    """Public, read-only view of a shared reading list — no account required."""

    serializer_class = SharedReadingListSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "share_token"
    lookup_url_kwarg = "token"

    def get_queryset(self):
        return (
            ReadingList.objects.filter(is_shared=True)
            .select_related("clinician__user")
            .prefetch_related("items__book")
        )
