"""Ayudas para que las listas del panel de administracion se lean mejor."""
from django.utils.html import format_html


def insignia(texto, clase):
    return format_html('<span class="ins ins-{}">{}</span>', clase, texto)


class AdminLegible:
    """Mixin: titulos claros en las listas y etiquetas con tildes en los formularios."""

    titulo_lista = None
    etiquetas = {}
    list_per_page = 25

    def changelist_view(self, request, extra_context=None):
        extra_context = {"title": self.titulo_lista or self.model._meta.verbose_name_plural.capitalize(),
                         **(extra_context or {})}
        return super().changelist_view(request, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for campo, etiqueta in self.etiquetas.items():
            if campo in form.base_fields:
                form.base_fields[campo].label = etiqueta
        return form
