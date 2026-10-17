"""Prepara las dos imagenes de un analisis para el comparador deslizable.

Las imagenes de "antes" y "despues" casi nunca cubren exactamente la misma zona
ni tienen el mismo tamano. Para que al deslizar coincidan punto por punto, se
recortan ambas a la misma caja geografica (la zona vigilada con un poco de
contexto) y se llevan al mismo tamano en pixeles. Los recortes se guardan en
media/ la primera vez y luego solo se reutilizan.
"""
import cv2
import numpy as np
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .detector import Limites, recortar
from .servicio import _leer, _limites, zona_vigilada

ANCHO_MAXIMO_PX = 1400
CONTEXTO = 0.25  # se muestra un 25 % mas alrededor de la zona vigilada


def _caja(analisis):
    """Zona vigilada + contexto, limitada a lo que cubren las dos imagenes."""
    zona = zona_vigilada(analisis.concesion)
    dlat = (zona.norte - zona.sur) * CONTEXTO
    dlon = (zona.este - zona.oeste) * CONTEXTO
    ampliada = Limites(zona.norte + dlat, zona.sur - dlat, zona.este + dlon, zona.oeste - dlon)
    comun = _limites(analisis.imagen_antes).interseccion(_limites(analisis.imagen_despues))
    return comun and comun.interseccion(ampliada)


def _a_puntos(coordenadas, caja, ancho, alto):
    """[[lon, lat], ...] -> "x,y x,y ..." en pixeles de la imagen recortada (para SVG)."""
    puntos = []
    for lon, lat in coordenadas:
        x = (lon - caja.oeste) / (caja.este - caja.oeste) * ancho
        y = (caja.norte - lat) / (caja.norte - caja.sur) * alto
        puntos.append(f"{x:.1f},{y:.1f}")
    return " ".join(puntos)


def _guardar(nombre, img):
    if not default_storage.exists(nombre):
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if ok:
            default_storage.save(nombre, ContentFile(jpg.tobytes()))
    return default_storage.url(nombre)


def preparar_comparacion(analisis, alertas=()):
    """Devuelve lo que necesita la plantilla _comparador.html, o None si no se puede."""
    if analisis is None or analisis.estado != analisis.Estado.COMPLETADO:
        return None
    caja = _caja(analisis)
    if caja is None:
        return None

    base = f"analisis/comparar/{analisis.pk}"
    nombre_antes, nombre_despues = f"{base}_antes.jpg", f"{base}_despues.jpg"

    if default_storage.exists(nombre_antes) and default_storage.exists(nombre_despues):
        with default_storage.open(nombre_antes) as f:
            alto, ancho = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR).shape[:2]
        url_antes, url_despues = default_storage.url(nombre_antes), default_storage.url(nombre_despues)
    else:
        antes = recortar(_leer(analisis.imagen_antes), _limites(analisis.imagen_antes), caja)
        despues = recortar(_leer(analisis.imagen_despues), _limites(analisis.imagen_despues), caja)
        if antes.size == 0 or despues.size == 0:
            return None
        # Mismo tamano para las dos: se usa el de mayor detalle, sin pasar el maximo.
        ancho = min(ANCHO_MAXIMO_PX, max(antes.shape[1], despues.shape[1]) * 2)
        alto = round(ancho * (caja.alto_m / caja.ancho_m))
        antes = cv2.resize(antes, (ancho, alto), interpolation=cv2.INTER_CUBIC)
        despues = cv2.resize(despues, (ancho, alto), interpolation=cv2.INTER_CUBIC)
        url_antes, url_despues = _guardar(nombre_antes, antes), _guardar(nombre_despues, despues)

    return {
        "antes": url_antes,
        "despues": url_despues,
        "ancho": ancho,
        "alto": alto,
        "fecha_antes": analisis.imagen_antes.vuelo.fecha_vuelo,
        "fecha_despues": analisis.imagen_despues.vuelo.fecha_vuelo,
        "limite": _a_puntos(analisis.concesion.limite, caja, ancho, alto),
        "alertas": [
            {"puntos": _a_puntos(a.poligono, caja, ancho, alto), "gravedad": a.gravedad, "id": a.pk}
            for a in alertas
        ],
    }
