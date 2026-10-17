from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.user.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Datos personales", {"fields": ("country", "date_birth")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("country", "date_birth")}),
    )
    list_display = ("id", "username", "email", "country", "is_staff")
