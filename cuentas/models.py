from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        TECNICO = "tecnico", "Técnico / Operador de dron"
        ANALISTA = "analista", "Analista forestal"
        CONCESIONARIO = "concesionario", "Concesionario"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CONCESIONARIO)
    concesionaria = models.ForeignKey(
        "concesiones.Concesionaria",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        help_text="Solo para usuarios con rol concesionario.",
    )
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "usuario"

    @property
    def es_tecnico(self):
        return self.rol == self.Rol.TECNICO or self.is_superuser

    @property
    def es_analista(self):
        return self.rol == self.Rol.ANALISTA or self.is_superuser

    @property
    def es_concesionario(self):
        return self.rol == self.Rol.CONCESIONARIO and not self.is_superuser
