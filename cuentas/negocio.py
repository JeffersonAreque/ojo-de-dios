"""Indicadores del negocio para el panel del administrador (mejora D).

Calcula cuantos clientes hay, que plan tiene cada uno, cuantas hectareas
se vigilan y cuanto ingresa al mes (MRR: ingreso mensual recurrente).
"""
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Q, Sum

from alertas.models import Alerta
from concesiones.models import Concesionaria


def resumen_negocio():
    precios = settings.PRECIOS_PLAN
    clientes = (
        Concesionaria.objects.filter(activa=True)
        .annotate(
            n_concesiones=Count("concesiones", distinct=True),
            hectareas=Sum("concesiones__area_ha"),
        )
        .order_by("razon_social")
    )
    confirmadas = dict(
        Alerta.objects.filter(estado=Alerta.Estado.CONFIRMADA)
        .values_list("concesion__concesionaria")
        .annotate(n=Count("id"))
    )

    filas, por_plan = [], {}
    for c in clientes:
        mensual = precios.get(c.plan, 0)
        filas.append({
            "cliente": c,
            "plan": c.get_plan_display(),
            "plan_clave": c.plan,
            "concesiones": c.n_concesiones,
            "hectareas": c.hectareas or Decimal(0),
            "mensual": mensual,
            "alertas": confirmadas.get(c.pk, 0),
        })
        plan = por_plan.setdefault(c.plan, {"nombre": c.get_plan_display(), "clientes": 0, "ingreso": 0})
        plan["clientes"] += 1
        plan["ingreso"] += mensual

    mrr = sum(f["mensual"] for f in filas)
    planes = []
    for clave, _ in Concesionaria.Plan.choices:
        p = por_plan.get(clave, {"nombre": Concesionaria.Plan(clave).label, "clientes": 0, "ingreso": 0})
        p["clave"] = clave
        p["precio"] = precios.get(clave, 0)
        p["pct"] = round(p["ingreso"] / mrr * 100) if mrr else 0
        planes.append(p)

    estados = Alerta.objects.aggregate(
        pendientes=Count("id", filter=Q(estado=Alerta.Estado.PENDIENTE)),
        confirmadas=Count("id", filter=Q(estado=Alerta.Estado.CONFIRMADA)),
    )
    return {
        "clientes": filas,
        "n_clientes": len(filas),
        "hectareas": sum((f["hectareas"] for f in filas), Decimal(0)),
        "n_concesiones": sum(f["concesiones"] for f in filas),
        "mrr": mrr,
        "anual": mrr * 12,
        "planes": planes,
        **estados,
    }
