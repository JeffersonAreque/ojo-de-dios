from django.contrib import admin

from .models import Imagen, Vuelo


class ImagenInline(admin.TabularInline):
    model = Imagen
    extra = 0


@admin.register(Vuelo)
class VueloAdmin(admin.ModelAdmin):
    list_display = ("concesion", "fecha_vuelo", "operador", "dron")
    list_filter = ("concesion",)
    inlines = [ImagenInline]
