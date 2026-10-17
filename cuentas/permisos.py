from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from concesiones.models import Concesion


def rol_requerido(*roles):
    """Permite el acceso solo a los roles indicados (el superusuario siempre entra)."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            usuario = request.user
            if not (usuario.is_superuser or usuario.rol in roles):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def concesiones_visibles(usuario):
    """Aislamiento por cliente: el concesionario solo ve sus propias concesiones."""
    qs = Concesion.objects.select_related("concesionaria")
    if usuario.es_concesionario:
        return qs.filter(concesionaria=usuario.concesionaria_id)
    return qs
