from django.urls import reverse
from rest_framework import serializers

from .models import Book, Review
from .services.affiliate import PROVIDERS, affiliate_url


class ReviewSerializer(serializers.ModelSerializer):
    clinician = serializers.StringRelatedField()
    clinician_verified = serializers.BooleanField(source='clinician.is_verified', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'clinician', 'clinician_verified', 'rating', 'content', 'created_at', 'updated_at']


class ReviewReadSerializer(serializers.ModelSerializer):
    """Read representation for the /api/reviews/ endpoint (includes book + clinician name)."""

    clinician = serializers.SerializerMethodField()
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'book', 'book_title', 'clinician', 'rating', 'content',
                  'created_at', 'updated_at']

    def get_clinician(self, obj):
        user = obj.clinician.user
        name = f"{user.first_name} {user.last_name}".strip()
        return {
            'id': obj.clinician_id,
            'name': name or user.username,
            'is_verified': obj.clinician.is_verified,
        }


class ReviewWriteSerializer(serializers.ModelSerializer):
    """Create/update a clinician review. The clinician is the request user (set in the view);
    `book` is required on create and immutable afterward."""

    class Meta:
        model = Review
        fields = ['id', 'book', 'rating', 'content', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:  # update — don't let a review move to another book
            self.fields['book'].read_only = True

    def validate(self, attrs):
        # On create, enforce one review per (book, clinician) with a friendly message
        # instead of a database IntegrityError.
        if self.instance is None:
            clinician = getattr(self.context['request'].user, 'clinician_profile', None)
            if clinician and Review.objects.filter(book=attrs.get('book'), clinician=clinician).exists():
                raise serializers.ValidationError("You have already reviewed this book.")
        return attrs


class BookListSerializer(serializers.ModelSerializer):
    cover = serializers.CharField(read_only=True)
    audience_score = serializers.IntegerField(read_only=True)  # Google aggregate (property, no query)
    critic_score = serializers.SerializerMethodField()
    clinician_review_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'subtitle', 'author', 'year_published', 'cover',
            'audience_score', 'google_ratings_count',
            'critic_score', 'clinician_review_count',
        ]

    def get_clinician_review_count(self, obj):
        # Uses the viewset annotation when present to avoid a per-row COUNT query.
        return getattr(obj, '_clinician_count', None) or obj.clinician_review_count

    def get_critic_score(self, obj):
        avg = getattr(obj, '_clinician_avg', None)
        if avg is None:
            avg = obj.clinician_average_rating
        return Book._to_percent(avg)


class BookDetailSerializer(serializers.ModelSerializer):
    cover = serializers.CharField(read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    # audience (Google) vs critic (clinicians)
    audience_score = serializers.IntegerField(read_only=True)
    critic_score = serializers.SerializerMethodField()
    clinician_average_rating = serializers.SerializerMethodField()
    clinician_review_count = serializers.SerializerMethodField()
    # tracked redirect URLs (per provider) — frontend links to these, not the retailer directly
    buy_links = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'google_books_id', 'isbn', 'isbn_10', 'title', 'subtitle', 'author',
            'description', 'publisher', 'published_date', 'year_published',
            'page_count', 'language', 'categories',
            'cover', 'cover_url', 'thumbnail_url', 'cover_source', 'info_link',
            'google_average_rating', 'google_ratings_count', 'audience_score',
            'clinician_average_rating', 'clinician_review_count', 'critic_score',
            'buy_links', 'reviews', 'last_synced_at',
        ]

    def _avg(self, obj):
        avg = getattr(obj, '_clinician_avg', None)
        return avg if avg is not None else obj.clinician_average_rating

    def get_clinician_average_rating(self, obj):
        avg = self._avg(obj)
        return round(float(avg), 2) if avg is not None else None

    def get_clinician_review_count(self, obj):
        return getattr(obj, '_clinician_count', None) or obj.clinician_review_count

    def get_critic_score(self, obj):
        return Book._to_percent(self._avg(obj))

    def get_buy_links(self, obj):
        request = self.context.get('request')
        links = {}
        for provider in PROVIDERS:
            if not affiliate_url(obj, provider):
                continue
            path = reverse('books:book-buy', args=[obj.pk]) + f"?provider={provider}"
            links[provider] = request.build_absolute_uri(path) if request else path
        return links


class BookSearchResultSerializer(serializers.Serializer):
    """A live Google Books search hit (not persisted)."""

    google_books_id = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    subtitle = serializers.CharField(allow_blank=True)
    author = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    isbn = serializers.CharField(allow_blank=True)
    thumbnail_url = serializers.CharField(allow_blank=True)
    average_rating = serializers.FloatField(allow_null=True)
    ratings_count = serializers.IntegerField(allow_null=True)
    year_published = serializers.IntegerField(allow_null=True)
    page_count = serializers.IntegerField(allow_null=True)


class ImportBookSerializer(serializers.Serializer):
    """Input for POST /api/books/import/. Provide exactly one of these."""

    volume_id = serializers.CharField(required=False, allow_blank=True)
    isbn = serializers.CharField(required=False, allow_blank=True)
    query = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(attrs.get(key) for key in ('volume_id', 'isbn', 'query')):
            raise serializers.ValidationError("Provide one of: volume_id, isbn, or query.")
        return attrs
