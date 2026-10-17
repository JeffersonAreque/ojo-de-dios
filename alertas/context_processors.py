from .models import Alerta


def pendientes(request):
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated or not usuario.es_analista:
        return {}
    return {"alertas_pendientes": Alerta.objects.filter(estado=Alerta.Estado.PENDIENTE).count()}
