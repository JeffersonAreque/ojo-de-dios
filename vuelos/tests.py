import io
import shutil
import tempfile
from io import StringIO

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image, TiffImagePlugin

from concesiones.models import Concesion
from cuentas.models import Usuario

from .models import Imagen

MEDIA_TEMPORAL = tempfile.mkdtemp()


def geotiff(oeste, norte, paso=0.0001, ancho=300, alto=300):
    img = Image.fromarray((np.random.rand(alto, ancho, 3) * 255).astype("uint8"))
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[33550] = (paso, paso, 0.0)
    tags.tagtype[33550] = 12
    tags[33922] = (0.0, 0.0, 0.0, oeste, norte, 0.0)
    tags.tagtype[33922] = 12
    salida = io.BytesIO()
    img.save(salida, format="TIFF", tiffinfo=tags)
    return SimpleUploadedFile("sentinel.tif", salida.getvalue(), "image/tiff")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RegistroVueloTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_login(Usuario.objects.get(username="tecnico"))
        self.concesion = Concesion.objects.get()

    def test_geotiff_completa_los_limites_y_se_guarda_como_png(self):
        r = self.client.post(reverse("vuelos:nuevo"), {
            "vuelo-concesion": self.concesion.pk, "vuelo-fecha_vuelo": "2026-10-20",
            "img-fuente": "satelite", "img-archivo": geotiff(-69.29, -12.805),
        })
        self.assertEqual(r.status_code, 302)
        img = Imagen.objects.latest("pk")
        self.assertTrue(img.archivo.name.endswith(".png"))
        self.assertAlmostEqual(img.norte, -12.805)
        self.assertAlmostEqual(img.sur, -12.835)
        self.assertEqual((img.ancho_px, img.alto_px), (300, 300))

    def test_rechaza_imagen_fuera_de_la_concesion(self):
        r = self.client.post(reverse("vuelos:nuevo"), {
            "vuelo-concesion": self.concesion.pk, "vuelo-fecha_vuelo": "2026-10-20",
            "img-fuente": "satelite", "img-archivo": geotiff(-70.5, -11.0),
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no cubre ninguna parte")
