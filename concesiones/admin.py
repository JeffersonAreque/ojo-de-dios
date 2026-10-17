from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Sum

from cuentas.admin_util import AdminLegible, insignia

from .models import Concesion, Concesionaria


class ConcesionInline(admin.TabularInline):
    model = Concesion
    fields = ("nombre", "codigo_contrato", "tipo", "area_ha")
    readonly_fields = ("area_ha",)
    extra = 0
    show_change_link = True
    verbose_name_plural = "Concesiones de este cliente"


@admin.register(Concesionaria)
class ConcesionariaAdmin(AdminLegible, admin.ModelAdmin):
    list_display = ("empresa", "ruc", "ver_plan", "n_concesiones", "hectareas", "mensualidad", "activa")
    list_filter = ("plan", "activa")
    search_fields = ("razon_social", "ruc", "contacto")
    inlines = [ConcesionInline]
    titulo_lista = "Clientes"
    etiquetas = {"razon_social": "Razón social", "ruc": "RUC", "telefono": "Teléfono", "correo": "Correo electrónico"}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _n=Count("concesiones", distinct=True), _ha=Sum("concesiones__area_ha"))

    @admin.display(description="Razón social", ordering="razon_social")
    def empresa(self, obj):
        return obj.razon_social

    @admin.display(description="Plan", ordering="plan")
    def ver_plan(self, obj):
        return insignia(obj.get_plan_display(), f"plan-{obj.plan}")

    @admin.display(description="Concesiones", ordering="_n")
    def n_concesiones(self, obj):
        return obj._n

    @admin.display(description="Hectáreas", ordering="_ha")
    def hectareas(self, obj):
        return f"{obj._ha or 0:,.1f}".replace(",", " ").replace(".", ",")

    @admin.display(description="Mensualidad")
    def mensualidad(self, obj):
        return f"S/ {settings.PRECIOS_PLAN.get(obj.plan, 0):,}".replace(",", " ")


@admin.register(Concesion)
class ConcesionAdmin(AdminLegible, admin.ModelAdmin):
    list_display = ("nombre", "codigo_contrato", "ver_cliente", "tipo", "area_ha")
    list_filter = ("tipo", "concesionaria")
    search_fields = ("nombre", "codigo_contrato", "concesionaria__razon_social")
    readonly_fields = ("area_ha",)
    titulo_lista = "Concesiones vigiladas"
    etiquetas = {"codigo_contrato": "Código de contrato", "limite": "Límite (coordenadas)", "area_ha": "Área (ha)"}

    @admin.display(description="Cliente", ordering="concesionaria__razon_social")
    def ver_cliente(self, obj):
        return obj.concesionaria.razon_social
