"""Engagement: how users interact with people and content.

Three concerns live here:
  * Follow     — the social graph (Letterboxd/Instagram style): who follows whom.
  * SavedBook  — a seeker bookmarking a book (the "watchlist" analog), with attribution.
  * Event      — an append-only clickstream log used to compute click-through and
                 conversion funnels (review -> clinician follow, affiliate clicks, etc.).

Follow + SavedBook are the app's source-of-truth *state* (what someone follows/has saved).
Event is the immutable *log* of every action, including the ones that didn't convert —
that's what makes click-through and funnel analysis possible.
"""
from django.conf import settings
from django.db import models


class Follow(models.Model):
    """A directional follow edge: ``follower`` follows ``followee``.

    The graph is general (any user may follow any other), but in practice seekers follow
    clinicians for their book recommendations. The reverse accessors live on the user model
    as ``user.following`` (people they follow) and ``user.followers`` (people following them).
    """

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_edges'
    )
    followee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='follower_edges'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followee')
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('followee')),
                name='engagement_follow_no_self_follow',
            ),
        ]

    def __str__(self):
        return f"{self.follower} → {self.followee}"


class SavedBook(models.Model):
    """A seeker bookmarking a book. ``via_review`` records which clinician review drove the
    save, so we can attribute saves back to the review that referred them (funnel signal)."""

    seeker = models.ForeignKey(
        'seekers.Seeker', on_delete=models.CASCADE, related_name='book_saves'
    )
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='seeker_saves')
    via_review = models.ForeignKey(
        'books.Review', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('seeker', 'book')

    def __str__(self):
        return f"{self.seeker} saved {self.book}"


class Event(models.Model):
    """An append-only clickstream record. Most fields are optional so any event type can
    reuse this one table; analytics queries filter by ``event_type`` and join the targets."""

    class Type(models.TextChoices):
        REVIEW_VIEWED = 'review_viewed', 'Review viewed'
        REVIEW_CLICKED = 'review_clicked', 'Review clicked'
        CLINICIAN_VIEWED = 'clinician_viewed', 'Clinician profile viewed'
        CLINICIAN_FOLLOWED = 'clinician_followed', 'Clinician followed'
        CLINICIAN_UNFOLLOWED = 'clinician_unfollowed', 'Clinician unfollowed'
        BOOK_VIEWED = 'book_viewed', 'Book viewed'
        BOOK_SAVED = 'book_saved', 'Book saved'
        BOOK_UNSAVED = 'book_unsaved', 'Book unsaved'
        SEARCH_PERFORMED = 'search_performed', 'Search performed'
        AFFILIATE_CLICKED = 'affiliate_clicked', 'Affiliate buy-link clicked'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='events',
    )
    session_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    event_type = models.CharField(max_length=40, choices=Type.choices, db_index=True)

    # Optional targets of the event.
    book = models.ForeignKey('books.Book', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    clinician = models.ForeignKey('clinicians.Clinician', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    review = models.ForeignKey('books.Review', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # Attribution: the review the user came *from* when this action happened (the funnel link).
    source_review = models.ForeignKey('books.Review', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    provider = models.CharField(max_length=20, blank=True, default='')  # e.g. affiliate provider
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
        ]

    def __str__(self):
        who = self.actor or self.session_id or 'anon'
        return f"{self.event_type} by {who}"
