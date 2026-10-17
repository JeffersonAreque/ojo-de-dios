import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from alertas.models import Alerta

from .detector import ErrorAnalisis, Limites, comparar
from .models import Analisis


def _leer(imagen):
    imagen.archivo.open("rb")
    datos = np.frombuffer(imagen.archivo.read(), np.uint8)
    imagen.archivo.close()
    img = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if img is None:
        raise ErrorAnalisis(f"No se pudo leer la imagen {imagen.pk}.")
    return img


def _limites(imagen):
    return Limites(imagen.norte, imagen.sur, imagen.este, imagen.oeste)


def ejecutar_analisis(concesion, imagen_antes, imagen_despues, usuario):
    """Compara dos imagenes de la concesion y registra las alertas pendientes."""
    analisis = Analisis(
        concesion=concesion,
        imagen_antes=imagen_antes,
        imagen_despues=imagen_despues,
        ejecutado_por=usuario,
    )
    try:
        resultado = comparar(
            _leer(imagen_antes), _limites(imagen_antes),
            _leer(imagen_despues), _limites(imagen_despues),
            area_minima_m2=settings.ANALISIS_AREA_MINIMA_M2,
        )
    except ErrorAnalisis as e:
        analisis.estado = Analisis.Estado.ERROR
        analisis.mensaje = str(e)
        analisis.save()
        return analisis

    with transaction.atomic():
        analisis.cobertura_antes_pct = resultado.cobertura_antes_pct
        analisis.cobertura_despues_pct = resultado.cobertura_despues_pct
        analisis.area_perdida_m2 = resultado.area_perdida_m2
        analisis.mensaje = f"{len(resultado.detecciones)} zona(s) con pérdida de cobertura. Umbral ExG antes/después: {resultado.umbral[0]} / {resultado.umbral[1]}"
        ok, png = cv2.imencode(".png", resultado.imagen_resultado)
        analisis.save()
        if ok:
            analisis.imagen_resultado.save(f"analisis_{analisis.pk}.png", ContentFile(png.tobytes()), save=True)

        Alerta.objects.bulk_create([
            Alerta(
                analisis=analisis,
                concesion=concesion,
                latitud=d.latitud,
                longitud=d.longitud,
                poligono=d.poligono,
                area_m2=d.area_m2,
                tipo_cambio=d.tipo_cambio,
                gravedad=d.gravedad,
                dentro_concesion=concesion.contiene(d.latitud, d.longitud),
            )
            for d in resultado.detecciones
        ])
    return analisis
