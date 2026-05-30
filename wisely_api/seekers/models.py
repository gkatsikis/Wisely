from django.conf import settings
from django.db import models


class Seeker(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seeker_profile'
    )
    saved_books = models.ManyToManyField(
        'books.Book', blank=True, related_name='saved_by_seekers'
    )

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
