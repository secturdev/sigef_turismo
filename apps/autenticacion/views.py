from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView
from mozilla_django_oidc.views import OIDCLogoutView

from apps.expediente.services import get_or_create_expediente

from .forms import EmailAuthenticationForm, RegisterForm


class RegisterView(FormView):
    template_name = "autenticacion/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("expediente:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("expediente:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        get_or_create_expediente(user)
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, "Cuenta creada. Completa tu expediente.")
        return super().form_valid(form)


class UserLoginView(LoginView):
    template_name = "autenticacion/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("expediente:dashboard")


class UserLogoutView(OIDCLogoutView):
    pass


class LlaveTabascoStartView(View):
    def get(self, request):
        return redirect("oidc_authentication_init")
