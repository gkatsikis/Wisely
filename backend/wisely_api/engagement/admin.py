from django.contrib import admin

from .models import Event, Follow, SavedBook


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followee', 'created_at')
    search_fields = ('follower__username', 'followee__username')
    raw_id_fields = ('follower', 'followee')
    date_hierarchy = 'created_at'


@admin.register(SavedBook)
class SavedBookAdmin(admin.ModelAdmin):
    list_display = ('seeker', 'book', 'via_review', 'created_at')
    search_fields = ('seeker__user__username', 'book__title')
    raw_id_fields = ('seeker', 'book', 'via_review')
    date_hierarchy = 'created_at'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'actor', 'session_id', 'book', 'clinician', 'provider', 'created_at')
    list_filter = ('event_type', 'provider', 'created_at')
    search_fields = ('actor__username', 'session_id')
    raw_id_fields = ('actor', 'book', 'clinician', 'review', 'source_review')
    date_hierarchy = 'created_at'
