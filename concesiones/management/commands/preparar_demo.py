"""Deja la base de datos lista para la exposicion.

  python manage.py preparar_demo              -> solo MUESTRA lo que haria (no cambia nada)
  python manage.py preparar_demo --confirmar  -> lo hace

Que hace:
  1. Borra la concesion de prueba "Bajo Tambopata (demo)" y las de practica (codigo PRACTICA...),
     con sus vuelos, imagenes, analisis y alertas.
  2. Borra analisis repetidos (mismas dos fechas) que no tienen ninguna alerta revisada.
  3. Borra los usuarios de prueba (Ana, Tomas, Carla); si alguno tiene registros, solo lo desactiva.
  4. Pone el nombre real de José al usuario "josee".
  5. Deja dos clientes de ejemplo en el panel del negocio, marcados como demostracion.
Todo ocurre en una sola transaccion: si algo falla, no se cambia nada.
"""
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ProtectedError

from alertas.models import Alerta
from analisis.models import Analisis
from concesiones.models import Concesion, Concesionaria
from cuentas.models import Usuario
from vuelos.models import Imagen, Vuelo

CODIGO_PRUEBA = "17-TAM/C-ECO-DEMO-01"
USUARIOS_PRUEBA = ["analista", "tecnico", "cliente"]
CLIENTES_EJEMPLO = [
    {"ruc": "20600000001", "razon_social": "Ecoturismo Río Tambopata S.A.C.", "plan": "basico",
     "contacto": "Cliente de demostración"},
    {"ruc": "20600000003", "razon_social": "Reforestadora Las Piedras S.A.C.", "plan": "enterprise",
     "contacto": "Cliente de demostración"},
]


class Command(BaseCommand):
    help = "Limpia los datos de prueba y deja la base lista para la exposición."

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true", help="Aplica los cambios (sin esto solo los muestra).")

    def handle(self, *args, confirmar=False, **opciones):
        self.archivos = []
        self.stdout.write(self.style.MIGRATE_HEADING(
            "Aplicando cambios..." if confirmar else "Vista previa (no se cambia nada). Usa --confirmar para aplicar."))
        with transaction.atomic():
            self._concesion_de_prueba()
            self._analisis_repetidos()
            self._usuarios_de_prueba()
            self._renombrar_jose()
            self._clientes_de_ejemplo()
            if not confirmar:
                transaction.set_rollback(True)
        if confirmar:
            for nombre in self.archivos:
                if nombre and default_storage.exists(nombre):
                    default_storage.delete(nombre)
            self.stdout.write(self.style.SUCCESS(f"Listo. Se borraron también {len(self.archivos)} archivos de imagen."))

    def _decir(self, texto):
        self.stdout.write(f"  · {texto}")

    def _archivos_de_analisis(self, analisis):
        self.archivos += [analisis.imagen_resultado.name,
                          f"analisis/comparar/{analisis.pk}_antes.jpg", f"analisis/comparar/{analisis.pk}_despues.jpg"]

    def _concesion_de_prueba(self):
        # La de prueba original y cualquier concesion de practica (codigo que empieza con PRACTICA)
        practica = list(Concesion.objects.filter(codigo_contrato__istartswith="PRACTICA"))
        original = Concesion.objects.filter(codigo_contrato=CODIGO_PRUEBA).first()
        if not practica and not original:
            self._decir("No hay concesiones de prueba ni de práctica.")
            return
        for c in practica + ([original] if original else []):
            self._borrar_concesion(c)

    def _borrar_concesion(self, concesion):
        analisis = list(concesion.analisis.all())
        for a in analisis:
            self._archivos_de_analisis(a)
        imagenes = Imagen.objects.filter(vuelo__concesion=concesion)
        self.archivos += [i.archivo.name for i in imagenes]
        n_alertas = Alerta.objects.filter(concesion=concesion).delete()[0]
        Analisis.objects.filter(concesion=concesion).delete()
        n_imagenes = imagenes.delete()[0]
        n_vuelos = Vuelo.objects.filter(concesion=concesion).delete()[0]
        concesion.delete()
        self._decir(f"Borrada «{concesion.nombre}»: {len(analisis)} análisis, {n_alertas} alertas, "
                    f"{n_vuelos} vuelos, {n_imagenes} imágenes.")

    def _analisis_repetidos(self):
        vistos = {}
        for a in Analisis.objects.order_by("ejecutado"):
            clave = (a.imagen_antes_id, a.imagen_despues_id)
            if clave not in vistos:
                vistos[clave] = a
                continue
            revisadas = a.alertas.exclude(estado=Alerta.Estado.PENDIENTE).count()
            if revisadas:
                self._decir(f"Análisis #{a.pk} repite las fechas del #{vistos[clave].pk}, pero tiene "
                            f"{revisadas} alertas revisadas: no se borra.")
                continue
            self._archivos_de_analisis(a)
            pk, n = a.pk, a.alertas.count()
            a.alertas.all().delete()
            a.delete()
            self._decir(f"Borrado el análisis #{pk} (repetía las fechas del #{vistos[clave].pk}), con {n} alertas pendientes.")

    def _usuarios_de_prueba(self):
        for nombre_usuario in USUARIOS_PRUEBA:
            u = Usuario.objects.filter(username=nombre_usuario).first()
            if not u or not u.is_active:
                continue
            try:
                with transaction.atomic():
                    u.delete()
                self._decir(f"Borrado el usuario de prueba «{nombre_usuario}» ({u.get_full_name()}).")
            except ProtectedError:
                u.is_active = False
                u.save(update_fields=["is_active"])
                self._decir(f"El usuario «{nombre_usuario}» tiene registros: se desactivó en lugar de borrarlo.")

    def _renombrar_jose(self):
        u = Usuario.objects.filter(username="josee").first()
        if not u:
            self._decir("No existe el usuario «josee».")
            return
        u.first_name, u.last_name = "José", "Huamán García"
        u.save(update_fields=["first_name", "last_name"])
        self._decir("El usuario «josee» ahora se muestra como José Huamán García (su contraseña no cambia).")

    def _clientes_de_ejemplo(self):
        for datos in CLIENTES_EJEMPLO:
            c, creado = Concesionaria.objects.update_or_create(ruc=datos["ruc"], defaults={**datos, "activa": True})
            self._decir(f"{'Creado' if creado else 'Actualizado'} el cliente de ejemplo «{c.razon_social}» (plan {c.get_plan_display()}).")
