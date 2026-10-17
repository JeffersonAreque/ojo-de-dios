from django.conf import settings
from django.db import models
from django.utils import timezone


class Alerta(models.Model):
    class Gravedad(models.TextChoices):
        BAJA = "baja", "Baja"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        CONFIRMADA = "confirmada", "Confirmada"
        DESCARTADA = "descartada", "Descartada"

    class TipoCambio(models.TextChoices):
        CLARO = "claro", "Claro en el dosel"
        TROCHA = "trocha", "Posible trocha"
        PERDIDA = "perdida", "Pérdida de cobertura extensa"

    analisis = models.ForeignKey("analisis.Analisis", on_delete=models.CASCADE, related_name="alertas")
    concesion = models.ForeignKey("concesiones.Concesion", on_delete=models.PROTECT, related_name="alertas")
    latitud = models.FloatField()
    longitud = models.FloatField()
    poligono = models.JSONField(help_text="Contorno del cambio detectado, [[lon, lat], ...]")
    area_m2 = models.FloatField()
    tipo_cambio = models.CharField(max_length=20, choices=TipoCambio.choices)
    gravedad = models.CharField(max_length=10, choices=Gravedad.choices)
    dentro_concesion = models.BooleanField(default=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="alertas_revisadas"
    )
    fecha_revision = models.DateTimeField(null=True, blank=True)
    comentario = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerta"
        ordering = ["-creado"]

    def __str__(self):
        return f"Alerta {self.pk} · {self.get_gravedad_display()} · {self.concesion.nombre}"

    @property
    def fecha_deteccion(self):
        return self.analisis.imagen_despues.vuelo.fecha_vuelo

    @property
    def area_ha(self):
        return round(self.area_m2 / 10_000, 2)

    @property
    def ubicacion_texto(self):
        return "Dentro de la concesión" if self.dentro_concesion else "Perímetro (zona de amortiguamiento)"

    def revisar(self, usuario, confirmar, comentario=""):
        self.estado = self.Estado.CONFIRMADA if confirmar else self.Estado.DESCARTADA
        self.revisado_por = usuario
        self.fecha_revision = timezone.now()
        self.comentario = comentario
        self.save(update_fields=["estado", "revisado_por", "fecha_revision", "comentario"])
