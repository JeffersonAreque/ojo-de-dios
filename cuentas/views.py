import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from alertas.models import Alerta
from alertas.views import alertas_visibles, alertas_geojson
from vuelos.models import Vuelo

from .negocio import resumen_negocio
from .permisos import concesiones_visibles, rol_requerido


@login_required
def inicio(request):
    concesiones = concesiones_visibles(request.user)
    alertas = alertas_visibles(request.user).exclude(estado=Alerta.Estado.DESCARTADA)
    conteo = alertas.aggregate(
        pendientes=Count("id", filter=Q(estado=Alerta.Estado.PENDIENTE)),
        confirmadas=Count("id", filter=Q(estado=Alerta.Estado.CONFIRMADA)),
        altas=Count("id", filter=Q(gravedad=Alerta.Gravedad.ALTA, estado=Alerta.Estado.CONFIRMADA)),
    )
    contexto = {
        "concesiones": concesiones,
        "total_vuelos": Vuelo.objects.filter(concesion__in=concesiones).count(),
        "conteo": conteo,
        "recientes": alertas.select_related("concesion", "analisis__imagen_despues__vuelo").order_by("-analisis__ejecutado", "-area_m2")[:6],
        "mapa_concesiones": [
            {"id": c.pk, "nombre": c.nombre, "limite": c.limite} for c in concesiones
        ],
        "mapa_alertas": alertas_geojson(alertas),
    }
    return render(request, "inicio.html", contexto)


@rol_requerido()  # sin roles: solo el administrador (superusuario)
def negocio(request):
    return render(request, "negocio.html", {"r": resumen_negocio()})
