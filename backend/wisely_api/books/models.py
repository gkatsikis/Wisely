from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


class Book(models.Model):
    class CoverSource(models.TextChoices):
        GOOGLE = 'google', 'Google Books'
        OPENLIBRARY = 'openlibrary', 'Open Library'
        MANUAL = 'manual', 'Manual upload'

    # Identity / external linkage
    google_books_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    isbn = models.CharField(max_length=20, blank=True, db_index=True)  # ISBN-13 preferred
    isbn_10 = models.CharField(max_length=20, blank=True, default='', db_index=True)  # ASIN for Amazon links

    # Core metadata (primarily sourced from Google Books)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, default='')
    author = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.CharField(max_length=10, blank=True, default='')  # YYYY / YYYY-MM / YYYY-MM-DD
    year_published = models.IntegerField(null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=10, blank=True, default='')
    categories = models.ManyToManyField('core.Category', related_name='books', blank=True)

    # Cover art
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)  # manual override
    cover_url = models.URLField(max_length=500, blank=True, default='')       # resolved best external cover
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')   # Google thumbnail (low-res)
    cover_source = models.CharField(max_length=20, choices=CoverSource.choices, blank=True, default='')

    # Aggregated "audience" rating from Google Books (Rotten-Tomatoes audience score)
    google_average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    google_ratings_count = models.PositiveIntegerField(null=True, blank=True)

    # Links / sync bookkeeping
    info_link = models.URLField(max_length=500, blank=True, default='')
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    # --- Scores: audience (Google) vs critic (clinicians), Rotten-Tomatoes style ---

    @staticmethod
    def _to_percent(rating):
        """Normalize a 0-5 rating to a 0-100 score."""
        if rating is None:
            return None
        return round(float(rating) / 5 * 100)

    @property
    def clinician_average_rating(self):
        """Average of clinician review ratings (1-5), or None when there are no reviews."""
        return self.reviews.aggregate(avg=Avg('rating'))['avg']

    @property
    def clinician_review_count(self):
        return self.reviews.count()

    @property
    def audience_score(self):
        """Google Books aggregate expressed as a 0-100 score."""
        return self._to_percent(self.google_average_rating)

    @property
    def critic_score(self):
        """Clinician aggregate expressed as a 0-100 score."""
        return self._to_percent(self.clinician_average_rating)

    @property
    def cover(self):
        """Best available cover URL: manual upload > resolved external cover > Google thumbnail."""
        if self.cover_image:
            return self.cover_image.url
        return self.cover_url or self.thumbnail_url or ''


class Review(models.Model):
    """A clinician's (critic) review of a book."""

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    clinician = models.ForeignKey(
        'clinicians.Clinician', on_delete=models.CASCADE, related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('book', 'clinician')

    def __str__(self):
        return f"Review by {self.clinician} for {self.book}"
