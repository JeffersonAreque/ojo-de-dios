from django.contrib import admin

from .models import Concesion, Concesionaria


@admin.register(Concesionaria)
class ConcesionariaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "ruc", "plan", "activa")
    list_filter = ("plan", "activa")
    search_fields = ("razon_social", "ruc")


@admin.register(Concesion)
class ConcesionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_contrato", "concesionaria", "tipo", "area_ha")
    list_filter = ("tipo",)
    search_fields = ("nombre", "codigo_contrato")
