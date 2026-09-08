from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCLogoutView,
)


OIDC_STATE_NOT_FOUND = "OIDC callback state not found in session `oidc_states`!"


class LlaveTabascoCallbackView(OIDCAuthenticationCallbackView):
    """Evita mostrar un error técnico al volver a un callback ya consumido."""

    def get(self, request):
        try:
            return super().get(request)
        except SuspiciousOperation as exc:
            if str(exc) != OIDC_STATE_NOT_FOUND:
                raise

            if request.user.is_authenticated:
                return redirect("expediente:dashboard")

            messages.warning(
                request,
                "El acceso de Llave Tabasco ya fue utilizado o expiró. "
                "Inicia sesión nuevamente.",
            )
            return redirect("autenticacion:login")


class UserLoginView(TemplateView):
    template_name = "autenticacion/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("expediente:dashboard")
        return super().dispatch(request, *args, **kwargs)


class UserLogoutView(OIDCLogoutView):
    pass


class LlaveTabascoStartView(View):
    def get(self, request):
        return redirect("oidc_authentication_init")
