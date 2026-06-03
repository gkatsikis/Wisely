from django.contrib import admin

from .models import Book, Review


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year_published',
                    'google_average_rating', 'google_ratings_count', 'cover_source')
    search_fields = ('title', 'author', 'isbn', 'google_books_id')
    list_filter = ('categories', 'cover_source', 'language')
    readonly_fields = ('last_synced_at',)
    inlines = [ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('book', 'clinician', 'rating')
    search_fields = ('book__title', 'clinician__user__username')
    list_filter = ('rating',)
