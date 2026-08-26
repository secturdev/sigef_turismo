from django.urls import path

from . import views

app_name = "muestras"

urlpatterns = [
    path(
        "evento/chocolate/solicitud/",
        views.Paso1View.as_view(),
        name="paso1",
    ),
    path(
        "evento/chocolate/solicitud/documentos/",
        views.Paso2View.as_view(),
        name="paso2",
    ),
    path(
        "evento/chocolate/solicitud/listo/",
        views.ListoView.as_view(),
        name="listo",
    ),
]
