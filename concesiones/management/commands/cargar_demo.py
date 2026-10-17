"""Carga datos de ejemplo para la demostracion.

Uso:
    python manage.py cargar_demo             # usuarios, concesion y 2 vuelos
    python manage.py cargar_demo --analizar  # ademas ejecuta el analisis
"""
from datetime import date

import cv2
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from analisis.servicio import ejecutar_analisis
from analisis.sintetico import generar_par
from concesiones.models import Concesion, Concesionaria
from cuentas.models import Usuario
from vuelos.models import Imagen, Vuelo

CLAVE_DEMO = "demo1234"

# Concesion ficticia en la zona de amortiguamiento de la RN Tambopata
LIMITE_DEMO = [
    [-69.2985, -12.8005], [-69.2715, -12.8010], [-69.2700, -12.8180],
    [-69.2760, -12.8295], [-69.2990, -12.8290],
]
MARGEN = 0.0015


class Command(BaseCommand):
    help = "Crea usuarios, una concesion y dos vuelos de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument("--analizar", action="store_true", help="Ejecuta tambien el analisis de cambio.")

    @transaction.atomic
    def handle(self, *args, **opciones):
        empresa, _ = Concesionaria.objects.get_or_create(
            ruc="20600000001",
            defaults={"razon_social": "Ecoturismo Río Tambopata S.A.C.", "contacto": "Gerencia de operaciones",
                      "plan": Concesionaria.Plan.PRO},
        )

        usuarios = {
            "admin": dict(rol=Usuario.Rol.ANALISTA, first_name="Administrador", is_superuser=True, is_staff=True),
            "analista": dict(rol=Usuario.Rol.ANALISTA, first_name="Ana", last_name="Analista"),
            "tecnico": dict(rol=Usuario.Rol.TECNICO, first_name="Tomás", last_name="Técnico"),
            "cliente": dict(rol=Usuario.Rol.CONCESIONARIO, first_name="Carla", last_name="Concesionaria",
                            concesionaria=empresa),
        }
        for nombre, datos in usuarios.items():
            u, creado = Usuario.objects.get_or_create(username=nombre, defaults=datos)
            if creado:
                u.set_password(CLAVE_DEMO)
                u.save()

        concesion, creada = Concesion.objects.get_or_create(
            codigo_contrato="17-TAM/C-ECO-DEMO-01",
            defaults={"concesionaria": empresa, "nombre": "Concesión Bajo Tambopata (demo)",
                      "tipo": Concesion.Tipo.ECOTURISMO, "sector": "Margen izquierda del río Tambopata",
                      "limite": LIMITE_DEMO},
        )

        if creada:
            caja = concesion.caja
            limites = dict(norte=caja["norte"] + MARGEN, sur=caja["sur"] - MARGEN,
                           este=caja["este"] + MARGEN, oeste=caja["oeste"] - MARGEN)
            antes, despues = generar_par()
            tecnico = Usuario.objects.get(username="tecnico")
            for fecha, img in [(date(2026, 8, 14), antes), (date(2026, 10, 12), despues)]:
                vuelo = Vuelo.objects.create(concesion=concesion, operador=tecnico, fecha_vuelo=fecha,
                                             dron="DJI Mavic 3 Multispectral", altitud_m=120)
                _, png = cv2.imencode(".png", img)
                imagen = Imagen(vuelo=vuelo, ancho_px=img.shape[1], alto_px=img.shape[0], **limites)
                imagen.archivo.save(f"demo_{fecha:%Y%m%d}.png", ContentFile(png.tobytes()), save=True)

        if opciones["analizar"]:
            imagenes = list(Imagen.objects.filter(vuelo__concesion=concesion).order_by("vuelo__fecha_vuelo"))
            analisis = ejecutar_analisis(concesion, imagenes[0], imagenes[-1], Usuario.objects.get(username="analista"))
            self.stdout.write(f"Análisis {analisis.pk}: {analisis.mensaje}")

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Usuarios: admin, analista, tecnico, cliente (contraseña: {CLAVE_DEMO})"
        ))
