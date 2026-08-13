from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, IdentityDocument


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'auth_method', 'is_verified', 'is_staff']
    list_filter = ['auth_method', 'is_verified', 'is_staff']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Authentication', {'fields': ('auth_method',)}),
        ('Verification', {'fields': ('is_verified', 'verified_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['verified_at']


@admin.register(IdentityDocument)
class IdentityDocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_type', 'document_number', 'submitted_at']
    list_filter = ['document_type']
    search_fields = ['user__email', 'document_number']
    readonly_fields = ['submitted_at', 'updated_at']

