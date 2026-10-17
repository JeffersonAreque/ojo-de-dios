"""Deteccion de cambios en la cobertura vegetal entre dos imagenes RGB.

Metodo (version 1 del piloto):
  1. Se recortan ambas imagenes a la zona geografica que comparten.
  2. Se calcula el indice de verdor ExG (Excess Green) normalizado
     y un umbral automatico (Otsu) para cada fecha:
         ExG = 2g - r - b,  con r, g, b = R/(R+G+B) ...
     La vegetacion tiene ExG alto; suelo desnudo, agua turbia o trochas, bajo.
  3. Pixel con vegetacion antes y sin vegetacion despues = perdida.
  4. Se limpian los pixeles sueltos (morfologia) y se agrupan en zonas.
  5. Cada zona con area minima se convierte en una deteccion con
     coordenadas, area en m2, tipo de cambio y gravedad.

No es un modelo entrenado: es la linea base contra la que se comparara
el modelo de IA de la fase 2 (segmentacion con imagenes etiquetadas).
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from concesiones.geo import METROS_POR_GRADO, metros_por_grado_lon

LADO_MAXIMO_PX = 3000
UMBRAL_MIN, UMBRAL_MAX = 0.03, 0.35


@dataclass
class Limites:
    norte: float
    sur: float
    este: float
    oeste: float

    @property
    def ancho_m(self):
        lat_media = (self.norte + self.sur) / 2
        return (self.este - self.oeste) * metros_por_grado_lon(lat_media)

    @property
    def alto_m(self):
        return (self.norte - self.sur) * METROS_POR_GRADO

    def interseccion(self, otro):
        caja = Limites(
            norte=min(self.norte, otro.norte),
            sur=max(self.sur, otro.sur),
            este=min(self.este, otro.este),
            oeste=max(self.oeste, otro.oeste),
        )
        if caja.norte <= caja.sur or caja.este <= caja.oeste:
            return None
        return caja


@dataclass
class Deteccion:
    latitud: float
    longitud: float
    poligono: list
    area_m2: float
    tipo_cambio: str
    gravedad: str


@dataclass
class Resultado:
    cobertura_antes_pct: float
    cobertura_despues_pct: float
    umbral: tuple
    detecciones: list = field(default_factory=list)
    imagen_resultado: np.ndarray = None

    @property
    def area_perdida_m2(self):
        return round(sum(d.area_m2 for d in self.detecciones), 1)


class ErrorAnalisis(Exception):
    pass


def indice_verdor(img_bgr):
    img = img_bgr.astype(np.float32) + 1.0
    b, g, r = cv2.split(img)
    total = b + g + r
    return (2 * g - r - b) / total


def umbral_vegetacion(indice):
    """Umbral de Otsu propio de cada imagen.

    Se calcula por separado para cada fecha porque la bruma, la hora y la
    estacion cambian el color del bosque entre una imagen y otra.
    """
    escalado = np.clip((indice.ravel() + 1) / 3 * 255, 0, 255).astype(np.uint8)
    t, _ = cv2.threshold(escalado, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    umbral = t / 255 * 3 - 1
    # Si casi todo es bosque, Otsu parte el bosque en dos (tonos claros y oscuros).
    # Por eso el umbral nunca supera el 60 % del verdor tipico (mediana) de la imagen.
    umbral = min(umbral, 0.6 * float(np.median(indice)))
    return float(np.clip(umbral, UMBRAL_MIN, UMBRAL_MAX))


def recortar(img, lim, caja):
    alto, ancho = img.shape[:2]
    x0 = round((caja.oeste - lim.oeste) / (lim.este - lim.oeste) * ancho)
    x1 = round((caja.este - lim.oeste) / (lim.este - lim.oeste) * ancho)
    y0 = round((lim.norte - caja.norte) / (lim.norte - lim.sur) * alto)
    y1 = round((lim.norte - caja.sur) / (lim.norte - lim.sur) * alto)
    return img[y0:y1, x0:x1]


def reducir(img):
    lado = max(img.shape[:2])
    if lado <= LADO_MAXIMO_PX:
        return img
    factor = LADO_MAXIMO_PX / lado
    return cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)


def clasificar(contorno, area_m2):
    (_, _), (w, h), _ = cv2.minAreaRect(contorno)
    alargamiento = max(w, h) / max(min(w, h), 1)
    if alargamiento >= 4:
        tipo = "trocha"
    elif area_m2 >= 10_000:
        tipo = "perdida"
    else:
        tipo = "claro"

    if area_m2 >= 5000:
        gravedad = "alta"
    elif area_m2 >= 1000 or tipo == "trocha":
        gravedad = "media"
    else:
        gravedad = "baja"
    return tipo, gravedad


def comparar(img_antes, lim_antes, img_despues, lim_despues, area_minima_m2=300):
    caja = lim_antes.interseccion(lim_despues)
    if caja is None:
        raise ErrorAnalisis("Las dos imágenes no cubren una zona en común.")

    antes = reducir(recortar(img_antes, lim_antes, caja))
    despues = recortar(img_despues, lim_despues, caja)
    if antes.size == 0 or despues.size == 0:
        raise ErrorAnalisis("La zona en común es demasiado pequeña.")
    despues = cv2.resize(despues, (antes.shape[1], antes.shape[0]), interpolation=cv2.INTER_AREA)

    alto, ancho = antes.shape[:2]
    m_por_px_x = caja.ancho_m / ancho
    m_por_px_y = caja.alto_m / alto
    area_px_m2 = m_por_px_x * m_por_px_y

    exg_antes = cv2.GaussianBlur(indice_verdor(antes), (5, 5), 0)
    exg_despues = cv2.GaussianBlur(indice_verdor(despues), (5, 5), 0)
    umbral_antes = umbral_vegetacion(exg_antes)
    umbral_despues = umbral_vegetacion(exg_despues)
    veg_antes = exg_antes > umbral_antes
    veg_despues = exg_despues > umbral_despues

    perdida = (veg_antes & ~veg_despues).astype(np.uint8) * 255
    # apertura pequena para no borrar trochas delgadas; cierre mayor para unir fragmentos
    perdida = cv2.morphologyEx(perdida, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    perdida = cv2.morphologyEx(perdida, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

    contornos, _ = cv2.findContours(perdida, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    def a_geo(x, y):
        lon = caja.oeste + (x / ancho) * (caja.este - caja.oeste)
        lat = caja.norte - (y / alto) * (caja.norte - caja.sur)
        return round(lat, 6), round(lon, 6)

    detecciones, validos = [], []
    for c in contornos:
        area_m2 = cv2.contourArea(c) * area_px_m2
        if area_m2 < area_minima_m2:
            continue
        m = cv2.moments(c)
        lat, lon = a_geo(m["m10"] / m["m00"], m["m01"] / m["m00"])
        simple = cv2.approxPolyDP(c, 1.5, True).reshape(-1, 2)
        poligono = [[lon_v, lat_v] for lat_v, lon_v in (a_geo(x, y) for x, y in simple)]
        tipo, gravedad = clasificar(c, area_m2)
        detecciones.append(Deteccion(lat, lon, poligono, round(area_m2, 1), tipo, gravedad))
        validos.append(c)

    detecciones.sort(key=lambda d: d.area_m2, reverse=True)

    marcada = despues.copy()
    capa = marcada.copy()
    cv2.drawContours(capa, validos, -1, (0, 0, 255), thickness=cv2.FILLED)
    marcada = cv2.addWeighted(capa, 0.35, marcada, 0.65, 0)
    cv2.drawContours(marcada, validos, -1, (0, 0, 255), thickness=2)

    return Resultado(
        cobertura_antes_pct=round(float(veg_antes.mean()) * 100, 2),
        cobertura_despues_pct=round(float(veg_despues.mean()) * 100, 2),
        umbral=(round(umbral_antes, 3), round(umbral_despues, 3)),
        detecciones=detecciones,
        imagen_resultado=marcada,
    )
