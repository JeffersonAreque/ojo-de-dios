import json

from django import forms

from cuentas.formularios import EstiloBootstrap

from .geo import validar_poligono
from .models import Concesion, Concesionaria


class ConcesionariaForm(EstiloBootstrap, forms.ModelForm):
    class Meta:
        model = Concesionaria
        fields = ["razon_social", "ruc", "contacto", "telefono", "correo", "plan"]


class ConcesionForm(EstiloBootstrap, forms.ModelForm):
    limite = forms.CharField(
        widget=forms.HiddenInput,
        error_messages={"required": "Dibuja el límite de la concesión en el mapa."},
    )

    class Meta:
        model = Concesion
        fields = ["concesionaria", "nombre", "codigo_contrato", "tipo", "sector", "limite"]

    def clean_limite(self):
        valor = self.cleaned_data["limite"]
        try:
            coords = json.loads(valor) if isinstance(valor, str) else valor
            return validar_poligono(coords)
        except (ValueError, TypeError, IndexError) as e:
            raise forms.ValidationError(f"Límite no válido: {e}")
