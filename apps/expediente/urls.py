from django.urls import path

from . import views

app_name = "expediente"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("eventos/", views.EventsView.as_view(), name="events"),
    path(
        "expediente/tipo-persona/",
        views.PersonTypeView.as_view(),
        name="person_type",
    ),
    path(
        "expediente/datos-generales/",
        views.GeneralDataView.as_view(),
        name="general_data",
    ),
    path(
        "expediente/documentos/",
        views.DocumentsView.as_view(),
        name="documents",
    ),
    path(
        "expediente/resumen/",
        views.SummaryView.as_view(),
        name="summary",
    ),
    path(
        "expediente/documentos/version/<int:version_id>/descargar/",
        views.download_document_version,
        name="download_version",
    ),
]
