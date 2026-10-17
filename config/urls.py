from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cuentas.views import inicio

admin.site.site_header = "Ojo de Dios · Administración"
admin.site.site_title = "Ojo de Dios"
admin.site.index_title = "Panel del negocio"
admin.site.enable_nav_sidebar = False

urlpatterns = [
    path("", inicio, name="inicio"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("concesiones/", include("concesiones.urls")),
    path("vuelos/", include("vuelos.urls")),
    path("analisis/", include("analisis.urls")),
    path("alertas/", include("alertas.urls")),
    path("admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
