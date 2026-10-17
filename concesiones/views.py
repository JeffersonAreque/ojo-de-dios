import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render

from alertas.models import Alerta
from alertas.views import alertas_geojson, alertas_visibles
from analisis.comparador import preparar_comparacion
from analisis.models import Analisis
from cuentas.models import Usuario
from cuentas.permisos import concesiones_visibles, rol_requerido

from .forms import ConcesionariaForm, ConcesionForm
from .models import Concesionaria


@login_required
def lista(request):
    confirmadas = Count("alertas", filter=Q(alertas__estado=Alerta.Estado.CONFIRMADA), distinct=True)
    concesiones = concesiones_visibles(request.user).annotate(
        n_confirmadas=confirmadas,
        ultimo_vuelo=Max("vuelos__fecha_vuelo"),
    )
    return render(request, "concesiones/lista.html", {"concesiones": concesiones})


@login_required
def detalle(request, pk):
    concesion = get_object_or_404(concesiones_visibles(request.user), pk=pk)
    alertas = (alertas_visibles(request.user).filter(concesion=concesion)
               .exclude(estado=Alerta.Estado.DESCARTADA).order_by("-area_m2"))
    ultimo = concesion.analisis.filter(estado=Analisis.Estado.COMPLETADO).select_related(
        "imagen_antes__vuelo", "imagen_despues__vuelo").first()
    comp = preparar_comparacion(ultimo, alertas.filter(analisis=ultimo)) if ultimo else None
    contexto = {
        "concesion": concesion,
        "ultimo": ultimo,
        "comp": comp,
        "alertas": alertas[:6],
        "total_alertas": alertas.count(),
        "vuelos": concesion.vuelos.select_related("operador").prefetch_related("imagenes"),
        "analisis": concesion.analisis.select_related("imagen_antes__vuelo", "imagen_despues__vuelo")[:5],
    }
    if comp is None:
        # Sin analisis todavia: el mapa sirve para ver donde esta la concesion.
        contexto["mapa_concesiones"] = [{"id": concesion.pk, "nombre": concesion.nombre, "limite": concesion.limite}]
        contexto["mapa_alertas"] = alertas_geojson(alertas)
    return render(request, "concesiones/detalle.html", contexto)


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
