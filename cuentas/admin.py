from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "rol", "concesionaria", "is_active")
    list_filter = ("rol", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Rol en la plataforma", {"fields": ("rol", "concesionaria", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Rol en la plataforma", {"fields": ("rol", "concesionaria")}),)
