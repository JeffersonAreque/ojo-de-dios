"""Calculos geograficos sencillos sin depender de PostGIS/GDAL.

Para areas de pocos km2 una proyeccion equirectangular local da un
error menor al 1%, suficiente para el piloto.
"""
import math

METROS_POR_GRADO = 111_320


def metros_por_grado_lon(lat):
    return METROS_POR_GRADO * math.cos(math.radians(lat))


def caja_envolvente(coords):
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    return {"norte": max(lats), "sur": min(lats), "este": max(lons), "oeste": min(lons)}


def area_poligono_ha(coords):
    if len(coords) < 3:
        return 0
    lat0 = sum(p[1] for p in coords) / len(coords)
    kx = metros_por_grado_lon(lat0)
    pts = [(p[0] * kx, p[1] * METROS_POR_GRADO) for p in coords]
    suma = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        suma += x1 * y2 - x2 * y1
    return abs(suma) / 2 / 10_000


def punto_en_poligono(lon, lat, coords):
    dentro = False
    j = len(coords) - 1
    for i in range(len(coords)):
        xi, yi = coords[i][0], coords[i][1]
        xj, yj = coords[j][0], coords[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def validar_poligono(coords):
    """Devuelve la lista de coordenadas limpia o lanza ValueError."""
    if not isinstance(coords, list) or len(coords) < 3:
        raise ValueError("El límite necesita al menos 3 vértices.")
    limpio = []
    for p in coords:
        lon, lat = float(p[0]), float(p[1])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Hay coordenadas fuera de rango.")
        limpio.append([round(lon, 6), round(lat, 6)])
    if limpio[0] == limpio[-1]:
        limpio.pop()
    return limpio
