from django.test import SimpleTestCase

from concesiones.geo import area_poligono_ha, punto_en_poligono

from .detector import ErrorAnalisis, Limites, comparar
from .sintetico import generar_par

LIM = Limites(norte=-12.800, sur=-12.830, este=-69.270, oeste=-69.300)


class DetectorTests(SimpleTestCase):
    def test_detecta_los_claros_y_la_trocha_nuevos(self):
        antes, despues = generar_par()
        r = comparar(antes, LIM, despues, LIM)
        self.assertEqual(len(r.detecciones), 3)
        self.assertIn("trocha", {d.tipo_cambio for d in r.detecciones})
        self.assertLess(r.cobertura_despues_pct, r.cobertura_antes_pct)

    def test_sin_cambios_no_genera_detecciones(self):
        antes, _ = generar_par()
        r = comparar(antes, LIM, antes.copy(), LIM)
        self.assertEqual(r.detecciones, [])

    def test_coordenadas_dentro_de_la_imagen(self):
        antes, despues = generar_par()
        for d in comparar(antes, LIM, despues, LIM).detecciones:
            self.assertTrue(LIM.sur <= d.latitud <= LIM.norte)
            self.assertTrue(LIM.oeste <= d.longitud <= LIM.este)

    def test_imagenes_sin_zona_comun(self):
        antes, despues = generar_par(200, 200)
        lejos = Limites(norte=-11.0, sur=-11.1, este=-70.0, oeste=-70.1)
        with self.assertRaises(ErrorAnalisis):
            comparar(antes, LIM, despues, lejos)


class GeoTests(SimpleTestCase):
    cuadrado = [[-69.30, -12.80], [-69.29, -12.80], [-69.29, -12.81], [-69.30, -12.81]]

    def test_area_aproximada(self):
        # ~1.085 km x 1.113 km ≈ 120.8 ha
        self.assertAlmostEqual(area_poligono_ha(self.cuadrado), 120.8, delta=1.5)

    def test_punto_en_poligono(self):
        self.assertTrue(punto_en_poligono(-69.295, -12.805, self.cuadrado))
        self.assertFalse(punto_en_poligono(-69.28, -12.805, self.cuadrado))
