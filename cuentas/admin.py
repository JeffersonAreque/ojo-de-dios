from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .admin_util import AdminLegible, insignia
from .models import Usuario

# Los permisos se manejan con el campo "rol", no con grupos de Django.
admin.site.unregister(Group)


@admin.register(Usuario)
class UsuarioAdmin(AdminLegible, UserAdmin):
    list_display = ("username", "nombre", "ver_rol", "concesionaria", "is_active", "last_login")
    titulo_lista = "Usuarios"
    list_filter = ("rol", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Rol en la plataforma", {"fields": ("rol", "concesionaria", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Rol en la plataforma", {"fields": ("rol", "concesionaria")}),)

    @admin.display(description="Rol", ordering="rol")
    def ver_rol(self, obj):
        if obj.is_superuser:
            return insignia("Administrador", "admin")
        return insignia(obj.get_rol_display(), f"rol-{obj.rol}")

    @admin.display(description="Nombre", ordering="first_name")
    def nombre(self, obj):
        return obj.get_full_name() or "—"
