from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('clinician', 'Clinician'),
        ('seeker', 'Seeker'),
        ('business_admin', 'Business Admin'),  # for future feature of moderator
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Social graph (Letterboxd/Instagram style): the users this user follows. In practice
    # seekers follow clinicians; the through model (engagement.Follow) records each edge.
    following = models.ManyToManyField(
        'self',
        through='engagement.Follow',
        through_fields=('follower', 'followee'),
        symmetrical=False,
        related_name='followers',
        blank=True,
    )

    def __str__(self):
        return self.username


class Category(models.Model):
    """Shared taxonomy: used both for book topics and clinician specialties."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
