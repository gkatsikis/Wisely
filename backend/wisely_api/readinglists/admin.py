from django.contrib import admin

from .models import ReadingList, ReadingListItem


class ReadingListItemInline(admin.TabularInline):
    model = ReadingListItem
    extra = 0
    raw_id_fields = ("book",)


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ("title", "clinician", "is_shared", "share_token", "created_at")
    search_fields = ("title", "clinician__user__username")
    list_filter = ("is_shared",)
    readonly_fields = ("share_token",)
    inlines = [ReadingListItemInline]
