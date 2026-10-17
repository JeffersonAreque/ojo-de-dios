from django import forms

from cuentas.formularios import EstiloBootstrap

from .georef import convertir_a_png, limites_geotiff
from .models import Imagen, Vuelo


class VueloForm(EstiloBootstrap, forms.ModelForm):
    class Meta:
        model = Vuelo
        fields = ["concesion", "fecha_vuelo", "dron", "altitud_m", "observaciones"]
        widgets = {
            "fecha_vuelo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, concesiones=None, **kwargs):
        super().__init__(*args, **kwargs)
        if concesiones is not None:
            self.fields["concesion"].queryset = concesiones


class ImagenForm(EstiloBootstrap, forms.ModelForm):
    class Meta:
        model = Imagen
        fields = ["archivo", "fuente", "norte", "sur", "este", "oeste"]
        labels = {"archivo": "Imagen (JPG, PNG o GeoTIFF)"}
        help_texts = {"archivo": "Si subes un GeoTIFF en WGS84, los límites se leen solos."}
        widgets = {campo: forms.NumberInput(attrs={"step": "0.000001"}) for campo in ["norte", "sur", "este", "oeste"]}

    LADOS = ["norte", "sur", "este", "oeste"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for lado in self.LADOS:
            self.fields[lado].required = False

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        self.limites_tiff = limites_geotiff(archivo)
        if archivo.name.lower().endswith((".tif", ".tiff")):
            archivo = convertir_a_png(archivo)
        return archivo

    def clean(self):
        datos = super().clean()
        geo = getattr(self, "limites_tiff", None)
        if geo and any(datos.get(k) is None for k in self.LADOS):
            datos.update(geo)
        n, s, e, o = (datos.get(k) for k in ["norte", "sur", "este", "oeste"])
        if None in (n, s, e, o):
            raise forms.ValidationError("La imagen debe estar georreferenciada: completa los cuatro límites.")
        if not (-90 <= s < n <= 90):
            raise forms.ValidationError("El límite norte debe ser mayor que el sur.")
        if not (-180 <= o < e <= 180):
            raise forms.ValidationError("El límite este debe ser mayor que el oeste.")
        return datos

    def validar_con_concesion(self, concesion):
        caja = concesion.caja
        d = self.cleaned_data
        se_cruzan = d["sur"] < caja["norte"] and d["norte"] > caja["sur"] and d["oeste"] < caja["este"] and d["este"] > caja["oeste"]
        if not se_cruzan:
            self.add_error(None, "La imagen no cubre ninguna parte de la concesión seleccionada.")
        return se_cruzan
