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

    def test_comparador_recorta_las_dos_fechas_al_mismo_tamano(self):
        from analisis.comparador import preparar_comparacion
        from analisis.models import Analisis
        from django.core.files.storage import default_storage
        from PIL import Image

        analisis = Analisis.objects.first()
        comp = preparar_comparacion(analisis, Alerta.objects.filter(analisis=analisis))
        self.assertIsNotNone(comp)
        tamanos = set()
        for clave in ("antes", "despues"):
            nombre = f"analisis/comparar/{analisis.pk}_{clave}.jpg"
            with default_storage.open(nombre) as f:
                tamanos.add(Image.open(f).size)
        self.assertEqual(tamanos, {(comp["ancho"], comp["alto"])})
        self.assertEqual(len(comp["alertas"]), Alerta.objects.filter(analisis=analisis).count())

    def test_paginas_muestran_el_comparador(self):
        from analisis.models import Analisis
        analisis = Analisis.objects.first()
        self.entrar("analista")
        self.assertContains(self.client.get(reverse("analisis:detalle", args=[analisis.pk])), "data-comparador")
        self.assertContains(self.client.get(reverse("concesiones:detalle", args=[analisis.concesion_id])), "data-comparador")

    def test_panel_del_negocio(self):
        from cuentas.negocio import resumen_negocio
        r = resumen_negocio()
        self.assertEqual(r["n_clientes"], len(r["clientes"]))
        self.assertEqual(r["mrr"], sum(f["mensual"] for f in r["clientes"]))
        self.assertEqual(r["anual"], r["mrr"] * 12)
        admin = Usuario.objects.create_superuser("jefe", "jefe@example.com", "x")
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("negocio"))
        self.assertContains(respuesta, "Panel del negocio")
        self.assertContains(respuesta, "Ingresos por plan")
        self.assertContains(self.client.get(reverse("admin:index")), "Volver al sistema")
        for url in ("alertas_alerta", "analisis_analisis", "concesiones_concesionaria",
                    "concesiones_concesion", "vuelos_vuelo", "cuentas_usuario"):
            self.assertEqual(self.client.get(reverse(f"admin:{url}_changelist")).status_code, 200, url)

    def test_solo_el_administrador_ve_el_negocio(self):
        for usuario in ("analista", "tecnico", "cliente"):
            self.entrar(usuario)
            self.assertEqual(self.client.get(reverse("negocio")).status_code, 403, usuario)

    def test_reporte_pdf_de_la_concesion(self):
        from analisis.models import Analisis
        analisis = Analisis.objects.first()
        alerta = Alerta.objects.filter(analisis=analisis).first()
        self.entrar("analista")
        self.client.post(reverse("alertas:detalle", args=[alerta.pk]), {"decision": "confirmar"})

        self.entrar("cliente")
        for formato in ("resumen", "tecnico"):
            respuesta = self.client.get(reverse("concesiones:reporte", args=[analisis.concesion_id]), {"formato": formato})
            self.assertEqual(respuesta.status_code, 200, formato)
            self.assertEqual(respuesta["Content-Type"], "application/pdf")
            self.assertTrue(respuesta.content.startswith(b"%PDF"))

    def test_no_se_repite_un_analisis_de_las_mismas_fechas(self):
        from analisis.forms import AnalisisForm
        from analisis.models import Analisis
        previo = Analisis.objects.first()
        form = AnalisisForm({"imagen_antes": previo.imagen_antes_id, "imagen_despues": previo.imagen_despues_id},
                            concesion=previo.concesion)
        self.assertFalse(form.is_valid())
        self.assertIn(f"Análisis #{previo.pk}", str(form.errors))

    def test_preparar_demo_borra_lo_de_prueba(self):
        from concesiones.models import Concesion
        call_command("preparar_demo", stdout=StringIO())  # vista previa: no cambia nada
        self.assertTrue(Concesion.objects.filter(codigo_contrato="17-TAM/C-ECO-DEMO-01").exists())
        from unittest import mock
        # Los archivos en disco no vuelven atras entre pruebas: aqui no se borran de verdad.
        with mock.patch("concesiones.management.commands.preparar_demo.default_storage.delete"):
            call_command("preparar_demo", "--confirmar", stdout=StringIO())
        self.assertFalse(Concesion.objects.filter(codigo_contrato="17-TAM/C-ECO-DEMO-01").exists())
        self.assertFalse(Usuario.objects.filter(username="cliente", is_active=True).exists())
