import secrets

from django.db import models


def generate_share_token():
    return secrets.token_urlsafe(12)


class ReadingList(models.Model):
    """A clinician's curated list of books (bibliotherapy). Shareable via `share_token` to
    a public, read-only view — a patient can open it without an account."""

    clinician = models.ForeignKey(
        'clinicians.Clinician', on_delete=models.CASCADE, related_name='reading_lists'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # The therapeutic intent of the list: what it's for / what the clinician hopes the
    # reader gets from it. Shown to the patient on the shared view.
    purpose = models.TextField(
        blank=True, default='',
        help_text="What this list is for — what you hope the reader gets out of it.",
    )
    books = models.ManyToManyField(
        'books.Book', through='ReadingListItem', related_name='reading_lists', blank=True
    )
    share_token = models.CharField(max_length=32, unique=True, default=generate_share_token, editable=False)
    is_shared = models.BooleanField(default=True)  # whether the public link is active
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.clinician})"


class ReadingListItem(models.Model):
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='+')
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    # Per-item annotation / chapter recommendations are intentionally deferred — add fields here.

    class Meta:
        unique_together = ('reading_list', 'book')
        ordering = ['position', 'id']

    def __str__(self):
        return f"{self.book} in list {self.reading_list_id}"
