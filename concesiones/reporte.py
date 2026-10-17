"""Reporte PDF de vigilancia por concesion (RF-005): dos documentos con el mismo contenido.

  resumen  Resumen ejecutivo de una pagina, para el dueno de la concesion.
  tecnico  Informe tecnico formal (secciones I a VI, con firmas), para ARFFS o SERFOR.

El contenido (cifras, conclusiones, recomendaciones) sale de reporte_datos.py.
"""
import io

import cv2
import numpy as np
from django.core.files.storage import default_storage
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .reporte_datos import a_utm, nombre, num, preparar_informe

VERDE = colors.HexColor("#12372A")
HOJA = colors.HexColor("#2F7D4F")
HOJA_CLARA = colors.HexColor("#4FA26F")
SEDIMENTO = colors.HexColor("#A88454")
PERDIDA = colors.HexColor("#C2185B")
NARANJA = colors.HexColor("#D9772B")
AMARILLO = colors.HexColor("#B8960C")
TINTA = colors.HexColor("#17231C")
GRIS = colors.HexColor("#5A6B60")
LINEA = colors.HexColor("#D6DED7")
FONDO = colors.HexColor("#F3F6F3")
COLOR_GRAVEDAD = {"alta": PERDIDA, "media": NARANJA, "baja": AMARILLO}
BGR_GRAVEDAD = {"alta": (91, 24, 194), "media": (43, 119, 217), "baja": (12, 150, 184)}
FORMATOS = {"resumen": "Resumen ejecutivo", "tecnico": "Informe técnico"}


def _hex(c):
    return c.hexval().replace("0x", "#")


def estilos(base=9.5):
    b = dict(fontName="Helvetica", fontSize=base, leading=base * 1.42, textColor=TINTA)
    return {
        "txt": ParagraphStyle("txt", **b),
        "just": ParagraphStyle("just", **{**b, "alignment": 4}),
        "peq": ParagraphStyle("peq", **{**b, "fontSize": base - 1.5, "leading": (base - 1.5) * 1.35, "textColor": GRIS}),
        "eti": ParagraphStyle("eti", **{**b, "fontName": "Helvetica-Bold", "fontSize": 7, "leading": 9, "textColor": GRIS}),
        "celda": ParagraphStyle("celda", **{**b, "fontSize": 8.2, "leading": 10.2}),
        "der": ParagraphStyle("der", **{**b, "fontSize": 8.2, "leading": 10.2, "alignment": TA_RIGHT}),
        "centro": ParagraphStyle("centro", **{**b, "alignment": TA_CENTER}),
        "h1": ParagraphStyle("h1", **{**b, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24, "textColor": VERDE}),
        "h2": ParagraphStyle("h2", **{**b, "fontName": "Helvetica-Bold", "fontSize": 11, "leading": 14, "textColor": VERDE,
                                      "spaceBefore": 9, "spaceAfter": 4}),
        "cifra": ParagraphStyle("cifra", **{**b, "fontName": "Helvetica-Bold", "fontSize": 19, "leading": 22, "textColor": VERDE}),
        "cifra_roja": ParagraphStyle("cr", **{**b, "fontName": "Helvetica-Bold", "fontSize": 19, "leading": 22, "textColor": PERDIDA}),
        "frase": ParagraphStyle("frase", **{**b, "fontSize": base + 2.5, "leading": (base + 2.5) * 1.4}),
    }


# ---------------------------------------------------------------- piezas comunes

def _puntos(texto):
    return np.array([[float(v) for v in p.split(",")] for p in texto.split()], np.int32)


def _imagen(inf, cual, ancho_mm, con_zonas=True, alto_max_mm=None):
    with default_storage.open(f"analisis/comparar/{inf.analisis.pk}_{cual}.jpg") as f:
        img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
    grosor = max(2, img.shape[1] // 350)
    if con_zonas:
        for a in inf.comp["alertas"]:
            cv2.polylines(img, [_puntos(a["puntos"])], True, BGR_GRAVEDAD[a["gravedad"]], grosor, cv2.LINE_AA)
    cv2.polylines(img, [_puntos(inf.comp["limite"])], True, (80, 225, 250), grosor + 1, cv2.LINE_AA)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    ancho, alto = ancho_mm, ancho_mm * img.shape[0] / img.shape[1]
    if alto_max_mm and alto > alto_max_mm:
        ancho, alto = ancho * alto_max_mm / alto, alto_max_mm
    return Image(io.BytesIO(jpg.tobytes()), width=ancho * mm, height=alto * mm)


def _logo(c, x, y, escala=1.0, trazo=colors.white):
    """Ojo cuya pupila es la copa de un arbol vista desde arriba (el logo del sistema)."""
    c.saveState()
    c.translate(x, y)
    c.scale(escala, escala)
    c.setStrokeColor(trazo)
    c.setLineWidth(1.6)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.curveTo(5, 8, 23, 8, 28, 0)
    p.curveTo(23, -8, 5, -8, 0, 0)
    c.drawPath(p, stroke=1, fill=0)
    for cx, cy, r, col in [(14, 0, 5.8, HOJA), (12, 1.4, 2.4, HOJA_CLARA), (16, 2, 2.1, colors.HexColor("#3E8F5D")),
                           (15.2, -1.8, 2.3, colors.HexColor("#24663F")), (12, -1.6, 1.7, SEDIMENTO)]:
        c.setFillColor(col)
        c.circle(cx, cy, r, stroke=0, fill=1)
    c.restoreState()


def _pie(c, doc, inf, ancho):
    c.saveState()
    c.setStrokeColor(LINEA)
    c.line(doc.leftMargin, 13 * mm, ancho - doc.rightMargin, 13 * mm)
    c.setFont("Helvetica", 7.2)
    c.setFillColor(GRIS)
    c.drawString(doc.leftMargin, 9 * mm, f"Ojo de Dios · Informe N.° {inf.numero} · Código de verificación {inf.codigo}")
    c.drawRightString(ancho - doc.rightMargin, 9 * mm, f"Página {doc.page}")
    c.restoreState()


def _tabla_zonas(inf, e, anchos, limite=None, con_utm=True):
    zonas = inf.zonas[:limite] if limite else inf.zonas
    cab = ["N.°", "Tipo de cambio", "Gravedad", "Ubicación", "Hectáreas"] + ([f"UTM {inf.zona_utm} (E · N)"] if con_utm else [])
    filas = [cab]
    for z in zonas:
        a = z.alerta
        fila = [str(a.pk), Paragraph(a.get_tipo_cambio_display(), e["celda"]),
                Paragraph(f"<font color='{_hex(COLOR_GRAVEDAD[a.gravedad])}'><b>{a.get_gravedad_display()}</b></font>", e["celda"]),
                "Dentro" if a.dentro_concesion else "Perímetro", Paragraph(num(a.area_ha, 2), e["der"])]
        if con_utm:
            fila.append(Paragraph(z.utm, e["celda"]))
        filas.append(fila)
    total = sum(z.alerta.area_m2 for z in zonas) / 10_000
    etiqueta = "Total" if not limite or limite >= len(inf.zonas) else f"{len(zonas)} de {len(inf.zonas)} zonas"
    filas.append(["", Paragraph(f"<b>{etiqueta}</b>", e["celda"]), "", "", Paragraph(f"<b>{num(total, 2)}</b>", e["der"])]
                 + ([""] if con_utm else []))
    t = Table(filas, colWidths=[w * mm for w in anchos], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 7.2),
        ("FONTSIZE", (0, 1), (-1, -1), 8.2), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, FONDO]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINEA), ("LINEABOVE", (0, -1), (-1, -1), 1, VERDE),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def _lista(items, e, estilo="txt"):
    return ListFlowable([ListItem(Paragraph(t, e[estilo]), leftIndent=13) for t in items], bulletType="1",
                        bulletFontSize=e[estilo].fontSize, bulletFontName="Helvetica-Bold", leftIndent=13,
                        bulletColor=VERDE, spaceBefore=0)


def _cifras(inf, e, ancho_total, n_cols=4):
    a = inf.analisis
    items = [(f"{num(inf.ha_total)} ha", "pérdida confirmada", True),
             (f"{num(inf.ha_dentro)} ha", "dentro de la concesión", False),
             (str(len(inf.zonas)), "zonas confirmadas", False),
             (f"{num(a.cobertura_antes_pct, 0)} a {num(a.cobertura_despues_pct, 0)} %", "cobertura vegetal", False)]
    filas = [[[Paragraph(v, e["cifra_roja"] if r else e["cifra"]), Paragraph(t, e["peq"])] for v, t, r in items[i:i + n_cols]]
             for i in range(0, len(items), n_cols)]
    t = Table(filas, colWidths=[ancho_total / n_cols] * n_cols)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FONDO), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LINEBEFORE", (0, 0), (-1, -1), 2.5, HOJA),
                           ("LINEBEFORE", (0, 0), (0, 0), 2.5, PERDIDA), ("LINEBELOW", (0, 0), (-1, -2), 3, colors.white),
                           ("LINEAFTER", (0, 0), (-2, -1), 3, colors.white)]))
    return t


def _validacion(inf, e, ancho_total, firmas=False):
    a = inf.analisis
    bloques = [("ANÁLISIS EJECUTADO POR", nombre(a.ejecutado_por),
                f"{timezone.localtime(a.ejecutado):%d/%m/%Y} · Análisis N.° {a.pk}"),
               ("ZONAS VALIDADAS POR", inf.revisores, "Analista forestal"),
               ("CÓDIGO DE VERIFICACIÓN", f"<b>{inf.codigo}</b>", "Cambia si se altera alguna zona.")]
    celdas = []
    for i, (eti, val, nota) in enumerate(bloques):
        celda = [Paragraph(eti, e["eti"]), Paragraph(val, e["txt"]), Paragraph(nota, e["peq"])]
        if firmas:
            celda = [Spacer(1, 13 * mm), Paragraph("_" * 32 if i < 2 else "&nbsp;", e["peq"])] + celda
        celdas.append(celda)
    t = Table([celdas], colWidths=[ancho_total / 3] * 3)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, VERDE), ("LINEAFTER", (0, 0), (-2, 0), 0.5, LINEA),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def _leyenda(e, ancho_total):
    items = [("Límite de la concesión", colors.HexColor("#E8C300")), ("Gravedad alta", PERDIDA),
             ("Gravedad media", NARANJA), ("Gravedad baja", AMARILLO)]
    fila, anchos, est = [], [], [("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, (texto, color) in enumerate(items):
        fila += ["", Paragraph(texto, e["peq"])]
        anchos += [5 * mm, ancho_total / 4 - 5 * mm]
        est += [("LINEBELOW", (2 * i, 0), (2 * i, 0), 2.5, color), ("BOTTOMPADDING", (2 * i, 0), (2 * i, 0), 5)]
    t = Table([fila], colWidths=anchos)
    t.setStyle(TableStyle(est))
    return t


def _ficha(pares, e, ancho_total, cols=2):
    filas = []
    for i in range(0, len(pares), cols):
        grupo = pares[i:i + cols]
        filas.append([[Paragraph(k.upper(), e["eti"]), Paragraph(v, e["txt"])] for k, v in grupo] + [""] * (cols - len(grupo)))
    t = Table(filas, colWidths=[ancho_total / cols] * cols)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA)]))
    return t


def _datos_generales(inf):
    c, cli = inf.concesion, inf.cliente
    este, norte, zona = a_utm(*inf.centro)
    return [("Titular", cli.razon_social), ("RUC", cli.ruc), ("Concesión", c.nombre), ("N.° de contrato", c.codigo_contrato),
            ("Tipo", c.get_tipo_display()), ("Superficie", f"{num(float(c.area_ha))} ha"),
            ("Ubicación", f"Madre de Dios · {c.sector}" if c.sector else "Madre de Dios"),
            (f"Punto central (UTM {zona})", f"{este} E · {norte} N")]


def _sin_analisis(e):
    return [Paragraph("Todavía no se ha comparado ningún par de imágenes de esta concesión. El informe se completará "
                      "cuando haya al menos dos vuelos analizados y revisados.", e["txt"])]


def _par_imagenes(inf, e, ancho_total, alto_max=None, figuras=False):
    mitad = ancho_total / mm / 2 - 2
    pie_a = f"<b>{'Figura 1. ' if figuras else ''}Antes</b> · {inf.fecha_antes:%d/%m/%Y}"
    pie_d = f"<b>{'Figura 2. ' if figuras else ''}Después</b> · {inf.fecha_despues:%d/%m/%Y}, con zonas confirmadas"
    t = Table([[_imagen(inf, "antes", mitad, False, alto_max), _imagen(inf, "despues", mitad, True, alto_max)],
               [Paragraph(pie_a, e["peq"]), Paragraph(pie_d, e["peq"])]], colWidths=[ancho_total / 2] * 2)
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


# ---------------------------------------------------------------- Informe tecnico formal

def _formato_tecnico(inf):
    e = estilos(9.6)
    ancho, alto = A4
    util = ancho - 40 * mm

    def encabezado(c, doc):
        c.saveState()
        _logo(c, 20 * mm, alto - 17 * mm, 1.05, trazo=VERDE)
        c.setFillColor(VERDE)
        c.setFont("Helvetica-Bold", 12.5)
        c.drawString(20 * mm + 36, alto - 15.4 * mm, "Ojo de Dios")
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRIS)
        c.drawString(20 * mm + 36, alto - 19.3 * mm, "Vigilancia forestal satelital")
        c.drawRightString(ancho - 20 * mm, alto - 15.4 * mm, f"Informe técnico N.° {inf.numero}")
        c.drawRightString(ancho - 20 * mm, alto - 19.3 * mm, f"Puerto Maldonado, {inf.emitido:%d/%m/%Y}")
        c.setStrokeColor(VERDE)
        c.setLineWidth(1.2)
        c.line(20 * mm, alto - 23 * mm, ancho - 20 * mm, alto - 23 * mm)
        c.restoreState()
        _pie(c, doc, inf, ancho)

    titulo = ParagraphStyle("t", parent=e["h1"], fontSize=15, leading=19, alignment=TA_CENTER)
    h = [Paragraph(f"INFORME TÉCNICO N.° {inf.numero}", titulo), Paragraph("Vigilancia de cobertura forestal", e["centro"]),
         Spacer(1, 6 * mm)]
    asunto = (f"Pérdida de cobertura forestal entre {inf.fecha_antes:%d/%m/%Y} y {inf.fecha_despues:%d/%m/%Y}"
              if inf.analisis else "Estado de vigilancia de la concesión")
    memo = Table([[Paragraph(f"<b>{k}</b>", e["txt"]), Paragraph(v, e["txt"])] for k, v in [
        ("A", f"{inf.cliente.razon_social}, titular de la {inf.concesion.nombre}"),
        ("DE", "Ojo de Dios · Área de análisis forestal"), ("ASUNTO", asunto), ("FECHA", f"{inf.emitido:%d/%m/%Y}")]],
        colWidths=[24 * mm, util - 24 * mm])
    memo.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LINEBELOW", (0, -1), (-1, -1), 0.8, LINEA)]))
    h += [memo, Spacer(1, 2 * mm), Paragraph("I. DATOS GENERALES", e["h2"]), _ficha(_datos_generales(inf), e, util)]
    if not inf.analisis:
        return h + _sin_analisis(e), encabezado, encabezado, A4

    h += [Paragraph("II. OBJETIVO", e["h2"]), Paragraph(inf.objetivo, e["just"]),
          Paragraph("III. METODOLOGÍA", e["h2"]), _ficha(inf.metodologia, e, util, cols=1),
          KeepTogether([Paragraph("IV. RESULTADOS", e["h2"]), _cifras(inf, e, util)]), Spacer(1, 4 * mm)]
    if inf.comp:
        h += [KeepTogether([_par_imagenes(inf, e, util, figuras=True), Spacer(1, 2 * mm), _leyenda(e, util)]), Spacer(1, 4 * mm)]
    h += [KeepTogether([Paragraph("<b>Tabla 1.</b> Zonas con pérdida de cobertura confirmada", e["peq"]), Spacer(1, 1.5 * mm),
                        _tabla_zonas(inf, e, (12, 50, 20, 22, 22, 44))]),
          Paragraph("V. CONCLUSIONES", e["h2"]), _lista(inf.conclusiones, e, "just"),
          Paragraph("VI. RECOMENDACIONES", e["h2"]), _lista(inf.recomendaciones, e, "just")]
    if inf.en_revision:
        h.append(Paragraph(f"Nota: el análisis N.° {inf.en_revision.pk}, más reciente, está en revisión y no se incluye.", e["peq"]))
    h += [Spacer(1, 5 * mm), KeepTogether([Paragraph("VALIDACIÓN", e["h2"]), _validacion(inf, e, util, firmas=True)])]
    return h, encabezado, encabezado, A4


# ---------------------------------------------------------------- Resumen ejecutivo (1 pagina)

def _formato_resumen(inf):
    e = estilos(9)
    ancho, alto = A4
    util = ancho - 32 * mm

    def encabezado(c, doc):
        c.saveState()
        c.setFillColor(VERDE)
        c.rect(0, alto - 22 * mm, ancho, 22 * mm, stroke=0, fill=1)
        _logo(c, 16 * mm, alto - 11 * mm, 1.0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(16 * mm + 34, alto - 9.8 * mm, "Ojo de Dios")
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#B9CCBF"))
        c.drawString(16 * mm + 34, alto - 13.6 * mm, "Resumen ejecutivo de vigilancia forestal")
        c.drawRightString(ancho - 16 * mm, alto - 9.8 * mm, f"N.° {inf.numero}")
        c.drawRightString(ancho - 16 * mm, alto - 13.6 * mm, f"{inf.emitido:%d/%m/%Y}")
        c.restoreState()
        _pie(c, doc, inf, ancho)

    h = [Paragraph(inf.concesion.nombre, e["h1"]),
         Paragraph(f"{inf.cliente.razon_social} · RUC {inf.cliente.ruc} · {num(float(inf.concesion.area_ha))} ha", e["peq"]),
         Spacer(1, 4 * mm)]
    if not inf.analisis:
        return h + _sin_analisis(e), encabezado, encabezado, A4

    frase = Table([[Paragraph(" ".join(inf.conclusiones[:2]), e["frase"])]], colWidths=[util])
    frase.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, 0), 3, PERDIDA if inf.zonas else HOJA), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    h += [frase, Spacer(1, 4 * mm), _cifras(inf, e, util), Spacer(1, 4 * mm)]
    if inf.comp:
        h += [_par_imagenes(inf, e, util, alto_max=55), Spacer(1, 2 * mm)]

    izq = [Paragraph("Zonas principales", e["h2"]), _tabla_zonas(inf, e, (10, 36, 17, 18, 18), limite=5, con_utm=False)]
    der = [Paragraph("Qué hacer", e["h2"]), _lista(inf.recomendaciones[:4], e, "celda")]
    dos = Table([[izq, der]], colWidths=[util * 0.57, util * 0.43])
    dos.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (0, 0), 8)]))
    h += [dos, Spacer(1, 4 * mm), _validacion(inf, e, util)]
    return h, encabezado, encabezado, A4


CONSTRUCTORES = {"resumen": _formato_resumen, "tecnico": _formato_tecnico}
MARGENES = {"resumen": (16, 16, 28), "tecnico": (20, 20, 30)}  # izquierda, derecha, arriba (mm)


def generar_reporte(concesion, usuario, formato="resumen"):
    """Devuelve (bytes del PDF, nombre de archivo)."""
    formato = formato if formato in CONSTRUCTORES else "resumen"
    inf = preparar_informe(concesion, usuario)
    historia, primera, siguientes, tam = CONSTRUCTORES[formato](inf)
    izq, der, arriba = MARGENES[formato]
    pdf = io.BytesIO()
    doc = SimpleDocTemplate(pdf, pagesize=tam, leftMargin=izq * mm, rightMargin=der * mm, topMargin=arriba * mm,
                            bottomMargin=18 * mm, title=f"{FORMATOS[formato]} · {concesion.nombre}", author="Ojo de Dios")
    doc.build(historia, onFirstPage=primera, onLaterPages=siguientes)
    prefijo = "resumen" if formato == "resumen" else "informe_tecnico"
    archivo = f"{prefijo}_{concesion.codigo_contrato.replace('/', '-')}_{inf.emitido:%Y%m%d}.pdf"
    return pdf.getvalue(), archivo
