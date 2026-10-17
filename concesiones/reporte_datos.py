"""Datos del informe de vigilancia, separados del diseno.

Aqui se decide QUE dice el informe (cifras, conclusiones, recomendaciones);
reporte.py decide COMO se ve. Asi se pueden probar varios formatos con el
mismo contenido.
"""
import hashlib
import math
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from alertas.models import Alerta
from analisis.comparador import preparar_comparacion
from analisis.models import Analisis
from analisis.servicio import zona_vigilada

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def num(valor, decimales=1):
    """1234.5 -> '1 234,5' (formato peruano)."""
    return f"{valor:,.{decimales}f}".replace(",", " ").replace(".", ",")


def mes(fecha):
    return f"{MESES[fecha.month - 1]} de {fecha.year}"


def nombre(usuario):
    return (usuario.get_full_name() or usuario.username) if usuario else "—"


def a_utm(lat, lon):
    """Lat/lon WGS84 -> (este, norte, zona) en UTM. Madre de Dios esta en la zona 19 Sur.
    SERFOR y OSINFOR trabajan en campo con UTM, por eso el informe las usa."""
    a, f = 6378137.0, 1 / 298.257223563
    k0, e2 = 0.9996, f * (2 - f)
    zona = int((lon + 180) / 6) + 1
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    fi, la = math.radians(lat), math.radians(lon)
    ep2 = e2 / (1 - e2)
    n = a / math.sqrt(1 - e2 * math.sin(fi) ** 2)
    t, c = math.tan(fi) ** 2, ep2 * math.cos(fi) ** 2
    aa = math.cos(fi) * (la - lon0)
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * fi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * fi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * fi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * fi))
    este = k0 * n * (aa + (1 - t + c) * aa ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * aa ** 5 / 120) + 500000
    norte = k0 * (m + n * math.tan(fi) * (aa ** 2 / 2 + (5 - t + 9 * c + 4 * c * c) * aa ** 4 / 24
                                          + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * aa ** 6 / 720))
    if lat < 0:
        norte += 10_000_000
    return round(este), round(norte), f"{zona}{'S' if lat < 0 else 'N'}"


@dataclass
class Zona:
    alerta: Alerta
    este: int
    norte: int

    @property
    def utm(self):
        return f"{self.este} E · {self.norte} N"


@dataclass
class Informe:
    concesion: object
    usuario: object
    emitido: object
    numero: str = ""
    codigo: str = ""
    analisis: object = None
    en_revision: object = None
    zonas: list = field(default_factory=list)
    comp: dict = None
    zona_utm: str = "19S"
    ha_total: float = 0
    ha_dentro: float = 0
    ha_vigilada: float = 0
    objetivo: str = ""
    conclusiones: list = field(default_factory=list)
    recomendaciones: list = field(default_factory=list)
    metodologia: list = field(default_factory=list)

    @property
    def cliente(self):
        return self.concesion.concesionaria

    @property
    def fecha_antes(self):
        return self.analisis.imagen_antes.vuelo.fecha_vuelo

    @property
    def fecha_despues(self):
        return self.analisis.imagen_despues.vuelo.fecha_vuelo

    @property
    def altas(self):
        return [z for z in self.zonas if z.alerta.gravedad == "alta"]

    @property
    def centro(self):
        caja = self.concesion.caja
        return (caja["norte"] + caja["sur"]) / 2, (caja["este"] + caja["oeste"]) / 2

    @property
    def revisores(self):
        return ", ".join(sorted({nombre(z.alerta.revisado_por) for z in self.zonas if z.alerta.revisado_por})) or "—"


def _elegir_analisis(concesion):
    """Se informa el ultimo analisis YA REVISADO; si hay uno mas nuevo pendiente, se avisa."""
    completados = (concesion.analisis.filter(estado=Analisis.Estado.COMPLETADO)
                   .select_related("imagen_antes__vuelo", "imagen_despues__vuelo", "ejecutado_por"))
    revisado = completados.filter(alertas__estado=Alerta.Estado.CONFIRMADA).distinct().first()
    nuevo = completados.first()
    en_revision = nuevo if (nuevo and revisado and nuevo.pk != revisado.pk and nuevo.ejecutado > revisado.ejecutado) else None
    return revisado or nuevo, en_revision


def preparar_informe(concesion, usuario):
    inf = Informe(concesion=concesion, usuario=usuario, emitido=timezone.localtime())
    inf.analisis, inf.en_revision = _elegir_analisis(concesion)
    if inf.analisis:
        confirmadas = (Alerta.objects.filter(analisis=inf.analisis, estado=Alerta.Estado.CONFIRMADA)
                       .select_related("revisado_por").order_by("-area_m2"))
        for a in confirmadas:
            este, norte, inf.zona_utm = a_utm(a.latitud, a.longitud)
            inf.zonas.append(Zona(a, este, norte))
        inf.comp = preparar_comparacion(inf.analisis, [z.alerta for z in inf.zonas])

    inf.numero = f"ODD-{inf.emitido:%Y}-{concesion.pk:03d}-{(inf.analisis.pk if inf.analisis else 0):04d}"
    huella = "|".join([inf.numero] + [f"{z.alerta.pk}:{z.alerta.estado}:{z.alerta.area_m2}" for z in inf.zonas])
    inf.codigo = hashlib.sha256(huella.encode()).hexdigest()[:12].upper()
    if inf.analisis:
        _redactar(inf)
    return inf


def _redactar(inf):
    """Objetivo, metodologia, conclusiones y recomendaciones, escritos a partir de los datos."""
    c, a = inf.concesion, inf.analisis
    zona = zona_vigilada(c)
    inf.ha_vigilada = zona.ancho_m * zona.alto_m / 10_000
    inf.ha_total = sum(z.alerta.area_m2 for z in inf.zonas) / 10_000
    inf.ha_dentro = sum(z.alerta.area_m2 for z in inf.zonas if z.alerta.dentro_concesion) / 10_000
    fa, fd = inf.fecha_antes, inf.fecha_despues
    margen = int(settings.ANALISIS_MARGEN_M)

    inf.objetivo = (f"Detectar y cuantificar la pérdida de cobertura forestal en la {c.nombre} y en su franja de "
                    f"vigilancia de {margen} m, entre {mes(fa)} y {mes(fd)}.")

    imagen = a.imagen_despues
    es_satelite = imagen.fuente == imagen.Fuente.SATELITE
    inf.metodologia = [
        ("Fuente de imágenes", f"{imagen.get_fuente_display()}" + (" Sentinel-2 L2A, color verdadero" if es_satelite else "")),
        ("Resolución", "10 m por píxel" if es_satelite else "Según el ortomosaico del vuelo"),
        ("Fechas comparadas", f"{fa:%d/%m/%Y} (antes) y {fd:%d/%m/%Y} (después)"),
        ("Área analizada", f"{num(inf.ha_vigilada, 0)} ha (concesión de {num(float(c.area_ha))} ha + franja de {margen} m)"),
        ("Método", "Índice de verdor ExG con umbral automático por imagen (Otsu); se marcan las zonas que "
                   f"pasaron de vegetación a suelo, de al menos {int(settings.ANALISIS_AREA_MINIMA_M2)} m²."),
        ("Revisión", "Cada zona fue revisada por un analista forestal, que la confirmó o la descartó "
                     "(nubes, sombras, agua o cambios naturales). Solo se informan las confirmadas."),
        ("Sistema de coordenadas", f"UTM WGS84, zona {inf.zona_utm}"),
    ]

    if not inf.zonas:
        inf.conclusiones = [f"Entre {mes(fa)} y {mes(fd)} no se confirmó pérdida de cobertura forestal en la "
                            f"concesión ni en su franja de {margen} m."]
        inf.recomendaciones = ["Mantener la vigilancia con una nueva imagen dentro de 30 días."]
        return

    pct_conc = inf.ha_dentro / float(c.area_ha) * 100 if c.area_ha else 0
    mayor = inf.zonas[0]
    trochas = [z for z in inf.zonas if z.alerta.tipo_cambio == Alerta.TipoCambio.TROCHA]
    inf.conclusiones = [
        f"Entre {mes(fa)} y {mes(fd)} se confirmó la pérdida de {num(inf.ha_total)} ha de cobertura forestal "
        f"en {len(inf.zonas)} zonas.",
        f"{num(inf.ha_dentro)} ha están dentro de la concesión, equivalentes al {num(pct_conc)} % de su superficie; "
        f"las {num(inf.ha_total - inf.ha_dentro)} ha restantes están en la franja de {margen} m.",
        f"La cobertura vegetal de la zona vigilada bajó de {num(a.cobertura_antes_pct, 0)} % a "
        f"{num(a.cobertura_despues_pct, 0)} %.",
        f"La zona más extensa (N.° {mayor.alerta.pk}, {num(mayor.alerta.area_ha, 2)} ha) se ubica "
        f"{'dentro de la concesión' if mayor.alerta.dentro_concesion else 'en el perímetro'}, en {mayor.utm}.",
    ]
    if trochas:
        inf.conclusiones.append(f"Se identificaron {len(trochas)} posibles trochas, que suelen indicar accesos "
                                "abiertos para extracción.")

    inf.recomendaciones = []
    if inf.altas:
        primeras = ", ".join(f"N.° {z.alerta.pk}" for z in inf.altas[:3])
        inf.recomendaciones.append(f"Verificar en campo las {len(inf.altas)} zonas de gravedad alta, empezando por "
                                   f"{primeras}, con las coordenadas UTM de este informe.")
    if inf.ha_dentro:
        inf.recomendaciones.append("Comunicar a la ARFFS Madre de Dios la pérdida dentro de la concesión, adjuntando "
                                   "este informe como sustento técnico.")
    if inf.ha_total > inf.ha_dentro:
        inf.recomendaciones.append(f"Vigilar la franja de {margen} m: la pérdida en el perímetro puede avanzar hacia "
                                   "la concesión.")
    if trochas:
        inf.recomendaciones.append("Revisar las posibles trochas para identificar y cerrar accesos no autorizados.")
    inf.recomendaciones.append("Programar una nueva imagen dentro de 30 días para dar seguimiento a las zonas.")
