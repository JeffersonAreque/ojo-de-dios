from django.contrib import admin

from cuentas.admin_util import AdminLegible, insignia

from .models import Analisis


@admin.register(Analisis)
class AnalisisAdmin(AdminLegible, admin.ModelAdmin):
    list_display = ("id", "ver_concesion", "fechas", "ver_estado", "cobertura", "perdida", "ejecutado_por", "ejecutado")
    list_filter = ("estado", "concesion")
    date_hierarchy = "ejecutado"
    titulo_lista = "Análisis de cambios"
    etiquetas = {"imagen_antes": "Imagen de antes", "imagen_despues": "Imagen de después",
                 "ejecutado_por": "Ejecutado por", "cobertura_antes_pct": "Cobertura antes (%)",
                 "cobertura_despues_pct": "Cobertura después (%)", "area_perdida_m2": "Área perdida (m²)",
                 "imagen_resultado": "Imagen de resultado", "concesion": "Concesión"}

    @admin.display(description="Fechas comparadas")
    def fechas(self, obj):
        return f"{obj.imagen_antes.vuelo.fecha_vuelo:%d/%m/%Y} → {obj.imagen_despues.vuelo.fecha_vuelo:%d/%m/%Y}"

    @admin.display(description="Estado", ordering="estado")
    def ver_estado(self, obj):
        return insignia(obj.get_estado_display(), "ok" if obj.estado == obj.Estado.COMPLETADO else "error")

    @admin.display(description="Cobertura")
    def cobertura(self, obj):
        if obj.cobertura_antes_pct is None:
            return "—"
        return f"{obj.cobertura_antes_pct:.1f} % → {obj.cobertura_despues_pct:.1f} %".replace(".", ",")

    @admin.display(description="Pérdida", ordering="area_perdida_m2")
    def perdida(self, obj):
        return f"{obj.area_perdida_ha:.1f} ha".replace(".", ",")

    @admin.display(description="Concesión", ordering="concesion__nombre")
    def ver_concesion(self, obj):
        return obj.concesion.nombre
