from django.db.models import Avg, Count, Q
from django.shortcuts import redirect
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsClinicianOrReadOnly, IsReviewAuthorOrReadOnly
from engagement.models import Event

from .models import Book, Review
from .serializers import (
    BookDetailSerializer,
    BookListSerializer,
    BookSearchResultSerializer,
    ImportBookSerializer,
    ReviewReadSerializer,
    ReviewWriteSerializer,
)
from .services import GoogleBooksClient, GoogleBooksError, import_book_from_volume
from .services.affiliate import PROVIDERS, affiliate_url

BOOK_ORDERING = {
    'title', '-title', 'year_published', '-year_published',
    'google_average_rating', '-google_average_rating',
}


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """The book catalog, plus live Google Books search/import and affiliate buy-links.

    - GET  /api/books/                 list the catalog; filter ?q= ?category=<id|name> ?ordering=
    - GET  /api/books/{id}/            detail: audience (Google) vs critic (clinician) scores
    - GET  /api/books/search/?q=       live Google Books search (not persisted)
    - POST /api/books/import/          import a volume into the catalog
    - GET  /api/books/{id}/buy/?provider=bookshop|amazon   log + redirect to the retailer
    """

    def get_queryset(self):
        qs = Book.objects.annotate(
            _clinician_avg=Avg('reviews__rating'),
            _clinician_count=Count('reviews'),
        )
        if self.action != 'list':
            return qs

        params = self.request.query_params
        q = params.get('q')
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(author__icontains=q) | Q(description__icontains=q)
            )
        category = params.get('category')
        if category:
            if category.isdigit():
                qs = qs.filter(categories__id=int(category))
            else:
                qs = qs.filter(categories__name__iexact=category)
        ordering = params.get('ordering')
        qs = qs.order_by(ordering if ordering in BOOK_ORDERING else 'title')
        return qs.distinct()

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


class ReviewViewSet(viewsets.ModelViewSet):
    """Clinician book reviews — the 'critic' side of Wisely.

    - GET    /api/reviews/?book=<id>&clinician=<id>   list (public)
    - POST   /api/reviews/                            create (clinicians only; one per book)
    - GET    /api/reviews/{id}/                       retrieve
    - PATCH/PUT /api/reviews/{id}/                    update own review
    - DELETE /api/reviews/{id}/                       delete own review
    """

    permission_classes = [IsClinicianOrReadOnly, IsReviewAuthorOrReadOnly]

    def get_queryset(self):
        qs = Review.objects.select_related('book', 'clinician__user').order_by('-created_at')
        book = self.request.query_params.get('book')
        if book and book.isdigit():
            qs = qs.filter(book_id=int(book))
        clinician = self.request.query_params.get('clinician')
        if clinician and clinician.isdigit():
            qs = qs.filter(clinician_id=int(clinician))
        return qs

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ReviewWriteSerializer
        return ReviewReadSerializer

    def perform_create(self, serializer):
        # The clinician is always the request user — never taken from the request body.
        serializer.save(clinician=self.request.user.clinician_profile)
