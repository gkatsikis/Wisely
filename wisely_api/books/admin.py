from django.contrib import admin

from .models import Book, Review


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year_published')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('categories',)
    inlines = [ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('book', 'clinician', 'rating')
    search_fields = ('book__title', 'clinician__user__username')
    list_filter = ('rating',)
