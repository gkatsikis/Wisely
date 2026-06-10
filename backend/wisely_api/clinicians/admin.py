from django.contrib import admin

from .models import (
    Clinician,
    ClinicianLicense,
    ClinicianSpecialty,
    License,
    ManualVerificationRequest,
)


class ClinicianLicenseInline(admin.TabularInline):
    model = ClinicianLicense
    extra = 1


@admin.register(Clinician)
class ClinicianAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_verified', 'npi', 'is_active', 'has_openings')
    search_fields = ('user__first_name', 'user__last_name', 'user__username', 'bio', 'npi')
    list_filter = ('is_verified', 'is_active', 'has_openings')
    readonly_fields = ('verified_at',)
    inlines = [ClinicianLicenseInline]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('license_type',)
    search_fields = ('license_type',)


@admin.register(ClinicianLicense)
class ClinicianLicenseAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'license', 'license_number',
                    'issued_state', 'expiration_date', 'is_verified')
    search_fields = ('clinician__user__first_name', 'clinician__user__last_name',
                     'license__license_type', 'license_number', 'issued_state')
    list_filter = ('license', 'issued_state', 'is_verified')


@admin.register(ClinicianSpecialty)
class ClinicianSpecialtyAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'category', 'description')
    search_fields = ('clinician__user__first_name',
                     'clinician__user__last_name', 'category__name')
    list_filter = ('category',)


@admin.register(ManualVerificationRequest)
class ManualVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('clinician', 'reason', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved')
    search_fields = ('clinician__user__username', 'clinician__user__last_name')
    date_hierarchy = 'created_at'
