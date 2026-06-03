from django.conf import settings
from django.db import models

from core.choices import STATE_CHOICES


class Seeker(models.Model):
    """A non-clinician member: browses books, reads clinician reviews, follows clinicians
    (via the engagement.Follow graph) for their recommendations, and bookmarks books."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seeker_profile'
    )
    birthdate = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=2, choices=STATE_CHOICES, blank=True, default='')
    # Topics they gravitate toward (book genres / themes). Grows organically as they browse.
    interests = models.ManyToManyField(
        'core.Category', blank=True, related_name='interested_seekers'
    )
    # Bookmarked books. The through model (engagement.SavedBook) records when each save
    # happened and which review drove it.
    saved_books = models.ManyToManyField(
        'books.Book',
        through='engagement.SavedBook',
        through_fields=('seeker', 'book'),
        related_name='saved_by_seekers',
        blank=True,
    )

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or self.user.username
