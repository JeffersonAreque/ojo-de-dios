"""Lectura de la georreferenciacion de un GeoTIFF y conversion a PNG.

Un GeoTIFF en WGS84 (EPSG:4326) sin rotacion guarda la esquina superior
izquierda en ModelTiepointTag y el tamano del pixel en ModelPixelScaleTag.
Con eso se calculan los limites norte/sur/este/oeste. Los navegadores no
muestran TIFF, por eso la imagen se guarda como PNG.
"""
import io

from django.core.files.base import ContentFile
from PIL import Image

TAG_ESCALA = 33550
TAG_PUNTO_AMARRE = 33922


def limites_geotiff(archivo):
    """Devuelve dict con norte/sur/este/oeste o None si no es un GeoTIFF util."""
    try:
        archivo.seek(0)
        with Image.open(archivo) as img:
            if img.format != "TIFF":
                return None
            tags = img.tag_v2
            escala, amarre = tags.get(TAG_ESCALA), tags.get(TAG_PUNTO_AMARRE)
            if not escala or not amarre:
                return None
            ancho, alto = img.size
            oeste, norte = float(amarre[3]), float(amarre[4])
            este = oeste + float(escala[0]) * ancho
            sur = norte - float(escala[1]) * alto
    except Exception:
        return None
    finally:
        archivo.seek(0)
    # si los valores no parecen grados, el TIFF esta en metros (UTM) y no se usa
    if not (-90 <= sur < norte <= 90 and -180 <= oeste < este <= 180):
        return None
    return {"norte": norte, "sur": sur, "este": este, "oeste": oeste}


def convertir_a_png(archivo):
    archivo.seek(0)
    with Image.open(archivo) as img:
        salida = io.BytesIO()
        img.convert("RGB").save(salida, format="PNG")
    nombre = archivo.name.rsplit(".", 1)[0] + ".png"
    return ContentFile(salida.getvalue(), name=nombre)
