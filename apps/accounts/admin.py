from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'must_change_password', 'is_staff']
    list_filter = ['role', 'must_change_password', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Campus Info', {'fields': ('role', 'must_change_password')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Campus Info', {'fields': ('role', 'must_change_password')}),
    )

admin.site.register(User, CustomUserAdmin)