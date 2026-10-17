from django import forms

from cuentas.formularios import EstiloBootstrap

from vuelos.models import Imagen


class ImagenChoice(forms.ModelChoiceField):
    def label_from_instance(self, img):
        return f"{img.vuelo.fecha_vuelo:%d/%m/%Y} · {img.get_fuente_display()} · vuelo {img.vuelo_id}"


class AnalisisForm(EstiloBootstrap, forms.Form):
    imagen_antes = ImagenChoice(queryset=Imagen.objects.none(), label="Fecha base (antes)")
    imagen_despues = ImagenChoice(queryset=Imagen.objects.none(), label="Fecha a comparar (después)")

    def __init__(self, *args, concesion=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Imagen.objects.filter(vuelo__concesion=concesion).select_related("vuelo")
        self.fields["imagen_antes"].queryset = qs
        self.fields["imagen_despues"].queryset = qs
        imagenes = list(qs.order_by("vuelo__fecha_vuelo"))
        if len(imagenes) >= 2 and not self.is_bound:
            self.initial = {"imagen_antes": imagenes[-2].pk, "imagen_despues": imagenes[-1].pk}

    def clean(self):
        datos = super().clean()
        antes, despues = datos.get("imagen_antes"), datos.get("imagen_despues")
        if antes and despues and antes.vuelo.fecha_vuelo >= despues.vuelo.fecha_vuelo:
            raise forms.ValidationError("La fecha base debe ser anterior a la fecha a comparar.")
        if antes and despues:
            from .models import Analisis
            previo = Analisis.objects.filter(
                imagen_antes=antes, imagen_despues=despues, estado=Analisis.Estado.COMPLETADO).first()
            if previo:
                raise forms.ValidationError(
                    f"Estas dos fechas ya se compararon en el Análisis #{previo.pk}. "
                    "Ábrelo desde la lista de análisis en lugar de repetirlo.")
        return datos
