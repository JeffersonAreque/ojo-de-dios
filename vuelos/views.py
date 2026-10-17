from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cuentas.models import Usuario
from cuentas.permisos import concesiones_visibles, rol_requerido

from .forms import ImagenForm, VueloForm
from .models import Vuelo


def vuelos_visibles(usuario):
    return Vuelo.objects.filter(concesion__in=concesiones_visibles(usuario)).select_related("concesion", "operador")


@login_required
def lista(request):
    vuelos = vuelos_visibles(request.user).prefetch_related("imagenes")
    concesion_id = request.GET.get("concesion")
    if concesion_id:
        vuelos = vuelos.filter(concesion_id=concesion_id)
    return render(request, "vuelos/lista.html", {
        "vuelos": vuelos,
        "concesiones": concesiones_visibles(request.user),
        "concesion_id": concesion_id,
    })


@login_required
def detalle(request, pk):
    vuelo = get_object_or_404(vuelos_visibles(request.user), pk=pk)
    imagenes = list(vuelo.imagenes.all())
    return render(request, "vuelos/detalle.html", {
        "vuelo": vuelo,
        "imagenes": imagenes,
        "mapa_concesiones": [{"id": vuelo.concesion_id, "nombre": vuelo.concesion.nombre, "limite": vuelo.concesion.limite}],
        "mapa_imagenes": [{"url": i.archivo.url, "limites": i.limites_leaflet} for i in imagenes],
    })


@rol_requerido(Usuario.Rol.TECNICO)
def nuevo(request):
    concesiones = concesiones_visibles(request.user)
    vuelo_form = VueloForm(request.POST or None, prefix="vuelo", concesiones=concesiones,
                           initial={"concesion": request.GET.get("concesion")})
    imagen_form = ImagenForm(request.POST or None, request.FILES or None, prefix="img")

    if request.method == "POST" and vuelo_form.is_valid() and imagen_form.is_valid():
        if imagen_form.validar_con_concesion(vuelo_form.cleaned_data["concesion"]):
            with transaction.atomic():
                vuelo = vuelo_form.save(commit=False)
                vuelo.operador = request.user
                vuelo.save()
                imagen = imagen_form.save(commit=False)
                imagen.vuelo = vuelo
                imagen.ancho_px = imagen.archivo.width
                imagen.alto_px = imagen.archivo.height
                imagen.save()
            messages.success(request, f"Vuelo del {vuelo.fecha_vuelo:%d/%m/%Y} registrado con su imagen.")
            return redirect("vuelos:detalle", pk=vuelo.pk)

    return render(request, "vuelos/form.html", {
        "vuelo_form": vuelo_form,
        "imagen_form": imagen_form,
        "cajas": {c.pk: c.caja for c in concesiones},
        "mapa_concesiones": [{"id": c.pk, "nombre": c.nombre, "limite": c.limite} for c in concesiones],
    })
