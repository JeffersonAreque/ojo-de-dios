from django import forms


class EstiloBootstrap:
    """Agrega las clases de Bootstrap a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            elif not isinstance(w, (forms.HiddenInput, forms.CheckboxInput)):
                w.attrs.setdefault("class", "form-control")
