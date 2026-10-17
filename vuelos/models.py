from django.conf import settings
from django.db import models


class Vuelo(models.Model):
    concesion = models.ForeignKey("concesiones.Concesion", on_delete=models.PROTECT, related_name="vuelos")
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vuelos")
    fecha_vuelo = models.DateField()
    dron = models.CharField(max_length=80, blank=True, help_text="Modelo del dron o fuente de la imagen.")
    altitud_m = models.PositiveIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vuelo"
        ordering = ["-fecha_vuelo"]

    def __str__(self):
        return f"{self.concesion.nombre} - {self.fecha_vuelo:%d/%m/%Y}"


class Imagen(models.Model):
    class Fuente(models.TextChoices):
        DRON = "dron", "Ortomosaico de dron"
        SATELITE = "satelite", "Imagen satelital"

    vuelo = models.ForeignKey(Vuelo, on_delete=models.PROTECT, related_name="imagenes")
    archivo = models.ImageField(upload_to="vuelos/%Y/%m/")
    fuente = models.CharField(max_length=20, choices=Fuente.choices, default=Fuente.DRON)
    # Limites geograficos de la imagen (georreferenciacion)
    norte = models.FloatField()
    sur = models.FloatField()
    este = models.FloatField()
    oeste = models.FloatField()
    ancho_px = models.PositiveIntegerField(default=0)
    alto_px = models.PositiveIntegerField(default=0)
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "imagen"
        ordering = ["-vuelo__fecha_vuelo"]
        verbose_name_plural = "imágenes"

    def __str__(self):
        return f"Imagen {self.pk} · {self.vuelo}"

    @property
    def limites_leaflet(self):
        return [[self.sur, self.oeste], [self.norte, self.este]]
