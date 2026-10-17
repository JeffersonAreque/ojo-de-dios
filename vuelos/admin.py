from django.contrib import admin

from cuentas.admin_util import AdminLegible

from .models import Imagen, Vuelo


class ImagenInline(admin.TabularInline):
    model = Imagen
    fields = ("archivo", "fuente", "norte", "sur", "este", "oeste", "ancho_px", "alto_px")
    extra = 0


@admin.register(Vuelo)
class VueloAdmin(AdminLegible, admin.ModelAdmin):
    list_display = ("fecha_vuelo", "ver_concesion", "dron", "operador", "n_imagenes")
    list_filter = ("concesion",)
    date_hierarchy = "fecha_vuelo"
    inlines = [ImagenInline]
    titulo_lista = "Vuelos e imágenes"
    etiquetas = {"fecha_vuelo": "Fecha del vuelo", "dron": "Dron o fuente", "altitud_m": "Altitud (m)",
                 "concesion": "Concesión"}

    @admin.display(description="Imágenes")
    def n_imagenes(self, obj):
        return obj.imagenes.count()

    @admin.display(description="Concesión", ordering="concesion__nombre")
    def ver_concesion(self, obj):
        return obj.concesion.nombre
