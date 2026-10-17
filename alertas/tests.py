import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from cuentas.models import Usuario

from .models import Alerta


MEDIA_TEMPORAL = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FlujoAlertasTests(TestCase):
    """Recorre el caso de uso CU-01 con los datos de demostracion."""

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", "--analizar", stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def entrar(self, usuario):
        self.client.force_login(Usuario.objects.get(username=usuario))

    def test_el_analisis_crea_alertas_pendientes(self):
        self.assertTrue(Alerta.objects.exists())
        self.assertFalse(Alerta.objects.exclude(estado=Alerta.Estado.PENDIENTE).exists())

    def test_concesionario_no_ve_alertas_sin_confirmar(self):
        alerta = Alerta.objects.first()
        self.entrar("cliente")
        self.assertEqual(self.client.get(reverse("alertas:detalle", args=[alerta.pk])).status_code, 404)

    def test_analista_confirma_y_el_concesionario_la_ve(self):
        alerta = Alerta.objects.first()
        self.entrar("analista")
        self.client.post(reverse("alertas:detalle", args=[alerta.pk]), {"decision": "confirmar"})
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, Alerta.Estado.CONFIRMADA)
        self.assertEqual(alerta.revisado_por.username, "analista")

        self.entrar("cliente")
        self.assertEqual(self.client.get(reverse("alertas:detalle", args=[alerta.pk])).status_code, 200)

    def test_descartada_no_llega_al_concesionario(self):
        alerta = Alerta.objects.first()
        self.entrar("analista")
        self.client.post(reverse("alertas:detalle", args=[alerta.pk]), {"decision": "descartar"})
        self.entrar("cliente")
        respuesta = self.client.get(reverse("alertas:historial"))
        self.assertNotIn(alerta, respuesta.context["alertas"])

    def test_concesionario_no_puede_revisar(self):
        alerta = Alerta.objects.first()
        alerta.revisar(Usuario.objects.get(username="analista"), True)
        self.entrar("cliente")
        r = self.client.post(reverse("alertas:detalle", args=[alerta.pk]), {"decision": "descartar"})
        self.assertEqual(r.status_code, 403)

    def test_permisos_por_rol(self):
        self.entrar("cliente")
        self.assertEqual(self.client.get(reverse("vuelos:nuevo")).status_code, 403)
        self.assertEqual(self.client.get(reverse("analisis:nuevo")).status_code, 403)
        self.entrar("tecnico")
        self.assertEqual(self.client.get(reverse("vuelos:nuevo")).status_code, 200)
        self.assertEqual(self.client.get(reverse("concesiones:nueva")).status_code, 403)
