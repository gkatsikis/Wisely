from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


class ProfessionalLicenseInline(admin.TabularInline):
    model = ProfessionalLicense
    extra = 1


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'has_openings')
    search_fields = ('user__first_name', 'user__last_name',
                     'user__username', 'bio')
    list_filter = ('is_active', 'has_openings')
    inlines = [ProfessionalLicenseInline]

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('__str__', )
    search_fields = ('user__first_name', 'user__last_name', 'user__username')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name', )


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
    list_display = ('book', 'professional', 'rating')
    search_fields = ('book__title', 'user__username')
    list_filter = ('rating', )


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('license_type', )
    search_fields = ('license_type', )


@admin.register(ProfessionalLicense)
class ProfessionalLicenseAdmin(admin.ModelAdmin):
    list_display = ('professional', 'license', 'license_number',
                    'issued_state', 'expiration_date', 'is_verified')
    search_fields = ('professional__user__first_name', 'professional__user__last_name',
                     'license__license_type', 'license_number', 'issued_state')
    list_filter = ('license', 'issued_state', 'is_verified')


@admin.register(ProfessionalSpecialty)
class ProfessionalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ('professional', 'category', 'description')
    search_fields = ('professional__user__first_name',
                     'professional__user__last_name', 'category__name')
    list_filter = ('category',)
