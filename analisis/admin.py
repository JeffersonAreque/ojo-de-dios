from django.contrib import admin

from .models import Analisis


@admin.register(Analisis)
class AnalisisAdmin(admin.ModelAdmin):
    list_display = ("id", "concesion", "estado", "area_perdida_m2", "ejecutado_por", "ejecutado")
    list_filter = ("estado", "concesion")
