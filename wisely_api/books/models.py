from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, blank=True)
    year_published = models.IntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    description = models.TextField(blank=True)
    categories = models.ManyToManyField('core.Category', related_name='books')

    def __str__(self):
        return self.title


class Review(models.Model):
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
