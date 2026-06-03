from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Category, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = UserAdmin.list_filter + ('user_type',)
    readonly_fields = ('created_at',)
    fieldsets = UserAdmin.fieldsets + (
        ('Wisely', {'fields': ('user_type', 'created_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Wisely', {'fields': ('user_type',)}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
