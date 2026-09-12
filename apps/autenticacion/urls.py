from django.urls import path

from . import views
from apps.landingpage.api import AvailableSpacesApiView

app_name = "autenticacion"

urlpatterns = [
    path(
        "api/v1/eventos/<int:event_id>/usuarios/<int:user_id>/espacios-disponibles/",
        AvailableSpacesApiView.as_view(),
        name="api_available_spaces",
    ),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("administracion/login/", views.AdminLoginView.as_view(), name="admin_login"),
    path(
        "administracion/",
        views.AdminDashboardView.as_view(),
        name="admin_dashboard",
    ),
    path(
        "administracion/usuarios/",
        views.AdminCreateView.as_view(),
        name="admin_users",
    ),
    path(
        "administracion/eventos/",
        views.EventListView.as_view(),
        name="admin_events",
    ),
    path(
        "administracion/eventos/nuevo/",
        views.EventCreateView.as_view(),
        name="admin_event_create",
    ),
    path(
        "administracion/eventos/boletab/datos/",
        views.BoletabEventsDataView.as_view(),
        name="admin_boletab_events_data",
    ),
    path(
        "administracion/eventos/<int:pk>/editar/",
        views.EventUpdateView.as_view(),
        name="admin_event_update",
    ),
    path(
        "administracion/eventos/<int:pk>/espacios/",
        views.EventSpacesView.as_view(),
        name="admin_event_spaces",
    ),
    path(
        "administracion/eventos/<int:pk>/espacios/datos/",
        views.EventSpacesDataView.as_view(),
        name="admin_event_spaces_data",
    ),
    path(
        "administracion/eventos/<int:pk>/espacios/secciones/",
        views.EventSectionsDataView.as_view(),
        name="admin_event_sections_data",
    ),
    path(
        "administracion/logout/",
        views.AdminLogoutView.as_view(),
        name="admin_logout",
    ),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("llave-tabasco/", views.LlaveTabascoStartView.as_view(), name="llave_tabasco"),
]
