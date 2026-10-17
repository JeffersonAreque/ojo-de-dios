from django import template

from cuentas.negocio import resumen_negocio as _resumen

register = template.Library()


@register.simple_tag
def resumen_negocio():
    return _resumen()
