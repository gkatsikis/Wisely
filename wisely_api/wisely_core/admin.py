from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'has_openings')
    search_fields = ('user__first_name', 'user__last_name',
                     'user__username', 'bio')
    list_filter = ('is_active', 'has_openings')


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1


class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year_published')
    search_fields = ('title', 'author', 'isbn')
    list_filter = ('categories',)
    inlines = [ReviewInline]


class ProfessionalLicenseInline(admin.TabularInline):
    model = ProfessionalLicense
    extra = 1


class ProfessionalWithLicensesAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'has_openings')
    list_filter = ('is_active', 'has_openings')
    inlines = [ProfessionalLicenseInline]


admin.site.register(User, UserAdmin)
admin.site.register(Professional, ProfessionalAdmin)
admin.site.register(Client)
admin.site.register(Category)
admin.site.register(Book, BookAdmin)
admin.site.register(Review)
admin.site.register(License)
admin.site.register(ProfessionalLicense)
admin.site.register(ProfessionalSpecialty)
