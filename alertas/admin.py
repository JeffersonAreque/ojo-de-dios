from django.contrib import admin

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("id", "concesion", "tipo_cambio", "gravedad", "estado", "area_m2", "creado")
    list_filter = ("estado", "gravedad", "concesion")
