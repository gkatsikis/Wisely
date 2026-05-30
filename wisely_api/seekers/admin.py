from django.contrib import admin

from .models import Seeker


@admin.register(Seeker)
class SeekerAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
