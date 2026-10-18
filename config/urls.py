from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cuentas.pwa import manifest, service_worker, sin_conexion
from cuentas.views import inicio, negocio

admin.site.site_header = "Ojo de Dios · Datos del sistema"
admin.site.site_title = "Ojo de Dios"
admin.site.index_title = "Datos del sistema"
admin.site.enable_nav_sidebar = False

urlpatterns = [
    path("", inicio, name="inicio"),
    path("negocio/", negocio, name="negocio"),
    path("manifest.webmanifest", manifest, name="manifest"),
    path("sw.js", service_worker, name="service_worker"),
    path("sin-conexion/", sin_conexion, name="sin_conexion"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("concesiones/", include("concesiones.urls")),
    path("vuelos/", include("vuelos.urls")),
    path("analisis/", include("analisis.urls")),
    path("alertas/", include("alertas.urls")),
    path("admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
