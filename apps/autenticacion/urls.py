from django.urls import path

from . import views

app_name = "autenticacion"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("llave-tabasco/", views.LlaveTabascoStartView.as_view(), name="llave_tabasco"),
]
