from django.db.models import Avg, Count
from django.shortcuts import redirect
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from engagement.models import Event

from .models import Book
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    BookSearchResultSerializer,
    ImportBookSerializer,
)
from .services import GoogleBooksClient, GoogleBooksError, import_book_from_volume
from .services.affiliate import PROVIDERS, affiliate_url


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """The book catalog, plus live Google Books search/import and affiliate buy-links.

    - GET  /api/books/                 list the local catalog
    - GET  /api/books/{id}/            detail: audience (Google) vs critic (clinician) scores
    - GET  /api/books/search/?q=       live Google Books search (not persisted)
    - POST /api/books/import/          import a volume into the catalog
    - GET  /api/books/{id}/buy/?provider=bookshop|amazon   log + redirect to the retailer
    """

    def get_queryset(self):
        return Book.objects.annotate(
            _clinician_avg=Avg('reviews__rating'),
            _clinician_count=Count('reviews'),
        ).order_by('title')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookListSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'detail': "Missing 'q' query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = min(int(request.query_params.get('limit', 10)), 40)
        except (TypeError, ValueError):
            limit = 10
        try:
            volumes = GoogleBooksClient().search(query, max_results=limit)
        except GoogleBooksError as exc:
            return Response(
                {'detail': f"Google Books request failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(BookSearchResultSerializer(volumes, many=True).data)

    @action(detail=False, methods=['post'], url_path='import')
    def import_volume(self, request):
        serializer = ImportBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        client = GoogleBooksClient()

        try:
            if data.get('volume_id'):
                volume = client.get_volume(data['volume_id'])
            elif data.get('isbn'):
                volume = client.get_by_isbn(data['isbn'])
            else:
                results = client.search(data['query'], max_results=1)
                volume = results[0] if results else None
        except GoogleBooksError as exc:
            return Response(
                {'detail': f"Google Books request failed: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not volume:
            return Response({'detail': "No matching volume found."}, status=status.HTTP_404_NOT_FOUND)

        book, created = import_book_from_volume(volume)
        book = self.get_queryset().get(pk=book.pk)  # re-fetch with score annotations
        output = BookDetailSerializer(book, context=self.get_serializer_context())
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'])
    def buy(self, request, pk=None):
        """Log an affiliate click, then 302 to the retailer.

        GET /api/books/{id}/buy/?provider=bookshop|amazon[&session_id=...]
        """
        provider = request.query_params.get('provider', '').lower()
        if provider not in PROVIDERS:
            return Response(
                {'detail': f"provider must be one of {list(PROVIDERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        book = self.get_object()
        url = affiliate_url(book, provider)
        if not url:
            return Response(
                {'detail': "No purchase link available for this book."},
                status=status.HTTP_404_NOT_FOUND,
            )
        Event.objects.create(
            event_type=Event.Type.AFFILIATE_CLICKED,
            actor=request.user if request.user.is_authenticated else None,
            session_id=request.query_params.get('session_id', ''),
            book=book,
            provider=provider,
        )
        return redirect(url)
