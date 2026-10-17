"""Genera un par de imagenes de prueba (antes / despues) de bosque.

Sirve para pruebas automaticas y para la demo cuando aun no hay
imagenes reales cargadas. La imagen 'despues' agrega dos claros y una
trocha que el detector deberia encontrar.
"""
import cv2
import numpy as np


def _bosque(ancho, alto, semilla):
    rng = np.random.default_rng(semilla)
    img = np.zeros((alto, ancho, 3), np.uint8)
    img[:] = (35, 85, 40)
    for _ in range(ancho * alto // 90):
        x, y = int(rng.integers(0, ancho)), int(rng.integers(0, alto))
        r = int(rng.integers(4, 11))
        verde = int(rng.integers(70, 140))
        color = (int(rng.integers(20, 50)), verde, int(rng.integers(25, 60)))
        cv2.circle(img, (x, y), r, color, -1)
    return img


def _rio(img):
    alto, ancho = img.shape[:2]
    puntos = np.array([[0, int(alto * 0.15)], [int(ancho * 0.3), int(alto * 0.25)],
                       [int(ancho * 0.6), int(alto * 0.12)], [ancho, int(alto * 0.2)]], np.int32)
    cv2.polylines(img, [puntos], False, (95, 140, 165), thickness=max(ancho // 30, 8))


def generar_par(ancho=900, alto=900, semilla=7):
    antes = _bosque(ancho, alto, semilla)
    _rio(antes)
    # claro preexistente (zona del albergue): no debe generar alerta
    cv2.rectangle(antes, (int(ancho * 0.08), int(alto * 0.75)), (int(ancho * 0.18), int(alto * 0.85)), (120, 150, 170), -1)

    despues = antes.copy()
    ruido = np.random.default_rng(semilla + 1).integers(-6, 7, despues.shape, dtype=np.int16)
    despues = np.clip(despues.astype(np.int16) + ruido, 0, 255).astype(np.uint8)

    suelo = (70, 110, 150)
    cv2.ellipse(despues, (int(ancho * 0.62), int(alto * 0.55)), (int(ancho * 0.07), int(alto * 0.05)), 20, 0, 360, suelo, -1)
    cv2.ellipse(despues, (int(ancho * 0.30), int(alto * 0.50)), (int(ancho * 0.03), int(alto * 0.025)), 0, 0, 360, suelo, -1)
    cv2.line(despues, (int(ancho * 0.45), int(alto * 0.70)), (int(ancho * 0.85), int(alto * 0.93)), suelo, max(ancho // 300, 3))
    return antes, despues
