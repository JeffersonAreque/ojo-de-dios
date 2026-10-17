from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from alertas.views import alertas_geojson, alertas_visibles
from cuentas.models import Usuario
from cuentas.permisos import concesiones_visibles, rol_requerido

from .comparador import preparar_comparacion
from .forms import AnalisisForm
from .models import Analisis
from .servicio import ejecutar_analisis


def analisis_visibles(usuario):
    return Analisis.objects.filter(concesion__in=concesiones_visibles(usuario)).select_related(
        "concesion", "imagen_antes__vuelo", "imagen_despues__vuelo", "ejecutado_por"
    )


@login_required
def lista(request):
    return render(request, "analisis/lista.html", {"lista": analisis_visibles(request.user)})


@rol_requerido(Usuario.Rol.TECNICO, Usuario.Rol.ANALISTA)
def nuevo(request):
    concesiones = concesiones_visibles(request.user)
    concesion = None
    if request.GET.get("concesion") or request.POST.get("concesion"):
        concesion = get_object_or_404(concesiones, pk=request.GET.get("concesion") or request.POST.get("concesion"))

    form = AnalisisForm(request.POST or None, concesion=concesion) if concesion else None
    if form and form.is_valid():
        analisis = ejecutar_analisis(
            concesion, form.cleaned_data["imagen_antes"], form.cleaned_data["imagen_despues"], request.user
        )
        if analisis.estado == Analisis.Estado.ERROR:
            messages.error(request, analisis.mensaje)
        else:
            messages.success(request, analisis.mensaje)
        return redirect("analisis:detalle", pk=analisis.pk)

    return render(request, "analisis/form.html", {"concesiones": concesiones, "concesion": concesion, "form": form})


@login_required
def detalle(request, pk):
    analisis = get_object_or_404(analisis_visibles(request.user), pk=pk)
    alertas = alertas_visibles(request.user).filter(analisis=analisis).order_by("-area_m2")
    c = analisis.concesion
    return render(request, "analisis/detalle.html", {
        "analisis": analisis,
        "comp": preparar_comparacion(analisis, alertas),
        "alertas": alertas,
        "mapa_concesiones": [{"id": c.pk, "nombre": c.nombre, "limite": c.limite}],
        "mapa_alertas": alertas_geojson(alertas),
        "mapa_imagenes": [
            {"url": analisis.imagen_despues.archivo.url, "limites": analisis.imagen_despues.limites_leaflet, "nombre": "Después"},
            {"url": analisis.imagen_antes.archivo.url, "limites": analisis.imagen_antes.limites_leaflet, "nombre": "Antes"},
        ],
    })
