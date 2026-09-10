from django.urls import path

from . import views

app_name = "autenticacion"

urlpatterns = [
    path("inicio/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("llave-tabasco/", views.LlaveTabascoStartView.as_view(), name="llave_tabasco"),
]
