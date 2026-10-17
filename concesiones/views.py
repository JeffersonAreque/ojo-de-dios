import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from alertas.models import Alerta
from alertas.views import alertas_geojson, alertas_visibles
from cuentas.models import Usuario
from cuentas.permisos import concesiones_visibles, rol_requerido

from .forms import ConcesionariaForm, ConcesionForm
from .models import Concesionaria


@login_required
def lista(request):
    concesiones = concesiones_visibles(request.user)
    return render(request, "concesiones/lista.html", {
        "concesiones": concesiones,
        "mapa_concesiones": [{"id": c.pk, "nombre": c.nombre, "limite": c.limite} for c in concesiones],
    })


@login_required
def detalle(request, pk):
    concesion = get_object_or_404(concesiones_visibles(request.user), pk=pk)
    alertas = alertas_visibles(request.user).filter(concesion=concesion).exclude(estado=Alerta.Estado.DESCARTADA)
    return render(request, "concesiones/detalle.html", {
        "concesion": concesion,
        "vuelos": concesion.vuelos.select_related("operador").prefetch_related("imagenes"),
        "analisis": concesion.analisis.select_related("imagen_antes__vuelo", "imagen_despues__vuelo")[:10],
        "alertas": alertas[:20],
        "mapa_concesiones": [{"id": concesion.pk, "nombre": concesion.nombre, "limite": concesion.limite}],
        "mapa_alertas": alertas_geojson(alertas),
    })


@rol_requerido(Usuario.Rol.ANALISTA)
def nueva(request):
    form = ConcesionForm(request.POST or None)
    if form.is_valid():
        concesion = form.save()
        messages.success(request, f"Concesión «{concesion.nombre}» registrada ({concesion.area_ha} ha).")
        return redirect("concesiones:detalle", pk=concesion.pk)
    return render(request, "concesiones/form.html", {"form": form})


@rol_requerido(Usuario.Rol.ANALISTA)
def concesionarias(request):
    form = ConcesionariaForm(request.POST or None)
    if form.is_valid():
        c = form.save()
        messages.success(request, f"Concesionaria «{c.razon_social}» registrada.")
        return redirect("concesiones:concesionarias")
    return render(request, "concesiones/concesionarias.html", {
        "form": form,
        "concesionarias": Concesionaria.objects.all(),
    })
