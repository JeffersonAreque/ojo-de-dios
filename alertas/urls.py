from django.urls import path

from . import views

app_name = "alertas"
urlpatterns = [
    path("", views.historial, name="historial"),
    path("<int:pk>/", views.detalle, name="detalle"),
]
