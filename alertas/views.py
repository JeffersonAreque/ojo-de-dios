import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from cuentas.permisos import concesiones_visibles

from .models import Alerta


def alertas_visibles(usuario):
    """El concesionario solo recibe alertas ya confirmadas por el analista (RF-003)."""
    qs = Alerta.objects.filter(concesion__in=concesiones_visibles(usuario)).select_related(
        "concesion", "analisis__imagen_despues__vuelo", "revisado_por"
    )
    if usuario.es_concesionario:
        qs = qs.filter(estado=Alerta.Estado.CONFIRMADA)
    return qs


def alertas_geojson(alertas):
    return [
        {
            "id": a.pk,
            "lat": a.latitud,
            "lon": a.longitud,
            "poligono": a.poligono,
            "gravedad": a.gravedad,
            "estado": a.estado,
            "tipo": a.get_tipo_cambio_display(),
            "area": a.area_m2,
            "fecha": a.fecha_deteccion.strftime("%d/%m/%Y"),
            "concesion": a.concesion.nombre,
        }
        for a in alertas
    ]


@login_required
def historial(request):
    alertas = alertas_visibles(request.user)
    filtros = {k: request.GET.get(k, "") for k in ["estado", "gravedad", "concesion"]}
    if filtros["estado"]:
        alertas = alertas.filter(estado=filtros["estado"])
    if filtros["gravedad"]:
        alertas = alertas.filter(gravedad=filtros["gravedad"])
    if filtros["concesion"]:
        alertas = alertas.filter(concesion_id=filtros["concesion"])

    if request.GET.get("formato") == "csv":
        return _csv(alertas)

    return render(request, "alertas/historial.html", {
        "alertas": alertas,
        "filtros": filtros,
        "concesiones": concesiones_visibles(request.user),
        "estados": Alerta.Estado.choices,
        "gravedades": Alerta.Gravedad.choices,
        "mapa_alertas": alertas_geojson(alertas),
    })


@login_required
def detalle(request, pk):
    alerta = get_object_or_404(alertas_visibles(request.user), pk=pk)

    if request.method == "POST":
        if not request.user.es_analista:
            raise PermissionDenied
        if alerta.estado != Alerta.Estado.PENDIENTE:
            messages.warning(request, "Esta alerta ya fue revisada.")
        else:
            confirmar = request.POST.get("decision") == "confirmar"
            alerta.revisar(request.user, confirmar, request.POST.get("comentario", "").strip())
            messages.success(request, "Alerta confirmada y visible para el concesionario." if confirmar
                             else "Detección descartada; no se notifica al concesionario.")
        siguiente = alertas_visibles(request.user).filter(estado=Alerta.Estado.PENDIENTE).order_by("creado").first()
        return redirect("alertas:detalle", pk=siguiente.pk) if siguiente else redirect("alertas:historial")

    c = alerta.concesion
    a = alerta.analisis
    return render(request, "alertas/detalle.html", {
        "alerta": alerta,
        "mapa_concesiones": [{"id": c.pk, "nombre": c.nombre, "limite": c.limite}],
        "mapa_alertas": alertas_geojson([alerta]),
        "mapa_imagenes": [
            {"url": a.imagen_despues.archivo.url, "limites": a.imagen_despues.limites_leaflet, "nombre": "Después"},
            {"url": a.imagen_antes.archivo.url, "limites": a.imagen_antes.limites_leaflet, "nombre": "Antes"},
        ],
    })


def _csv(alertas):
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="historial_alertas.csv"'
    respuesta.write("﻿")
    w = csv.writer(respuesta)
    w.writerow(["id", "concesion", "fecha_deteccion", "tipo", "gravedad", "estado", "area_m2",
                "latitud", "longitud", "ubicacion", "revisado_por", "fecha_revision", "comentario"])
    for a in alertas:
        w.writerow([a.pk, a.concesion.nombre, a.fecha_deteccion, a.get_tipo_cambio_display(), a.get_gravedad_display(),
                    a.get_estado_display(), a.area_m2, a.latitud, a.longitud, a.ubicacion_texto,
                    a.revisado_por or "", a.fecha_revision or "", a.comentario])
    return respuesta
