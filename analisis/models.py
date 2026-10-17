from django.conf import settings
from django.db import models


class Analisis(models.Model):
    class Estado(models.TextChoices):
        COMPLETADO = "completado", "Completado"
        ERROR = "error", "Error"

    concesion = models.ForeignKey("concesiones.Concesion", on_delete=models.PROTECT, related_name="analisis")
    imagen_antes = models.ForeignKey("vuelos.Imagen", on_delete=models.PROTECT, related_name="+")
    imagen_despues = models.ForeignKey("vuelos.Imagen", on_delete=models.PROTECT, related_name="+")
    ejecutado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="analisis")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.COMPLETADO)
    cobertura_antes_pct = models.FloatField(null=True)
    cobertura_despues_pct = models.FloatField(null=True)
    area_perdida_m2 = models.FloatField(default=0)
    imagen_resultado = models.ImageField(upload_to="analisis/", blank=True)
    mensaje = models.TextField(blank=True)
    ejecutado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analisis"
        ordering = ["-ejecutado"]
        verbose_name_plural = "análisis"

    def __str__(self):
        return (
            f"Análisis {self.pk}: {self.imagen_antes.vuelo.fecha_vuelo:%d/%m/%Y}"
            f" → {self.imagen_despues.vuelo.fecha_vuelo:%d/%m/%Y}"
        )

    @property
    def area_perdida_ha(self):
        return round(self.area_perdida_m2 / 10_000, 1)

    @property
    def variacion_cobertura(self):
        if self.cobertura_antes_pct is None or self.cobertura_despues_pct is None:
            return None
        return round(self.cobertura_despues_pct - self.cobertura_antes_pct, 2)
