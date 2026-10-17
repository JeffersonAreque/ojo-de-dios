from django.contrib import admin

from cuentas.admin_util import AdminLegible, insignia

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(AdminLegible, admin.ModelAdmin):
    list_display = ("id", "ver_concesion", "tipo", "ver_gravedad", "ver_estado", "hectareas", "zona", "detectada")
    ordering = ("-creado", "-area_m2")
    list_display_links = ("id", "tipo")
    list_filter = ("estado", "gravedad", "tipo_cambio", "concesion")
    search_fields = ("concesion__nombre", "comentario")
    date_hierarchy = "creado"
    readonly_fields = ("analisis", "latitud", "longitud", "poligono", "area_m2", "creado")
    titulo_lista = "Alertas detectadas"
    etiquetas = {"tipo_cambio": "Tipo de cambio", "dentro_concesion": "Dentro de la concesión",
                 "revisado_por": "Revisado por", "fecha_revision": "Fecha de revisión", "area_m2": "Área (m²)",
                 "poligono": "Polígono", "analisis": "Análisis", "concesion": "Concesión"}

    @admin.display(description="Tipo", ordering="tipo_cambio")
    def tipo(self, obj):
        return obj.get_tipo_cambio_display()

    @admin.display(description="Gravedad", ordering="gravedad")
    def ver_gravedad(self, obj):
        return insignia(obj.get_gravedad_display(), obj.gravedad)

    @admin.display(description="Estado", ordering="estado")
    def ver_estado(self, obj):
        return insignia(obj.get_estado_display(), obj.estado)

    @admin.display(description="Hectáreas", ordering="area_m2")
    def hectareas(self, obj):
        return f"{obj.area_m2 / 10_000:,.2f}".replace(",", " ").replace(".", ",")

    @admin.display(description="Ubicación", ordering="dentro_concesion")
    def zona(self, obj):
        return "Dentro" if obj.dentro_concesion else "Perímetro"

    @admin.display(description="Concesión", ordering="concesion__nombre")
    def ver_concesion(self, obj):
        return obj.concesion.nombre

    @admin.display(description="Detectada", ordering="creado")
    def detectada(self, obj):
        return obj.analisis.imagen_despues.vuelo.fecha_vuelo.strftime("%d/%m/%Y")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("concesion", "analisis__imagen_despues__vuelo")
