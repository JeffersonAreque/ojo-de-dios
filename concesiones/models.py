from django.core.validators import RegexValidator
from django.db import models

from .geo import area_poligono_ha, caja_envolvente, punto_en_poligono


class Concesionaria(models.Model):
    class Plan(models.TextChoices):
        BASICO = "basico", "Básico"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    razon_social = models.CharField(max_length=150)
    ruc = models.CharField(
        max_length=11,
        unique=True,
        validators=[RegexValidator(r"^(10|20)\d{9}$", "El RUC debe tener 11 dígitos y empezar con 10 o 20.")],
    )
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.BASICO)
    activa = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "concesionaria"
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social


class Concesion(models.Model):
    class Tipo(models.TextChoices):
        ECOTURISMO = "ecoturismo", "Ecoturismo"
        CONSERVACION = "conservacion", "Conservación"
        MADERABLE = "maderable", "Maderable"

    concesionaria = models.ForeignKey(Concesionaria, on_delete=models.PROTECT, related_name="concesiones")
    nombre = models.CharField(max_length=150)
    codigo_contrato = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.ECOTURISMO)
    sector = models.CharField(max_length=150, blank=True, help_text="Referencia de ubicación, p. ej. margen del río Tambopata.")
    # Poligono en formato GeoJSON: [[lon, lat], [lon, lat], ...]
    limite = models.JSONField()
    area_ha = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "concesion"
        ordering = ["nombre"]
        verbose_name_plural = "concesiones"

    def __str__(self):
        return f"{self.nombre} ({self.codigo_contrato})"

    def save(self, *args, **kwargs):
        self.area_ha = round(area_poligono_ha(self.limite), 2)
        super().save(*args, **kwargs)

    @property
    def caja(self):
        return caja_envolvente(self.limite)

    def contiene(self, lat, lon):
        return punto_en_poligono(lon, lat, self.limite)
