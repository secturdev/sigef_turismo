from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .constants import EVENTO_NOMBRE
from .forms import Paso1Form, Paso2Form
from .services import get_or_create_solicitud, guardar_paso1, guardar_paso2


def _datos_globales(user):
    from apps.expediente.models import DatosGenerales, Expediente

    try:
        expediente = user.expediente
    except Expediente.DoesNotExist:
        return None

    try:
        datos = expediente.datos_generales
    except DatosGenerales.DoesNotExist:
        datos = None

    return {
        "tipo_persona": expediente.get_tipo_persona_display()
        if expediente.tipo_persona
        else "—",
        "nombres": getattr(datos, "nombres", "") or "—",
        "telefono": getattr(datos, "telefono", "") or "—",
        "correo": getattr(datos, "correo_contacto", "") or user.correo,
        "curp": getattr(datos, "curp", "") or "—",
        "representante_legal": getattr(datos, "representante_legal", "") or "—",
    }


class Paso1View(LoginRequiredMixin, FormView):
    template_name = "muestras/paso1.html"
    form_class = Paso1Form
    login_url = "autenticacion:login"
    success_url = reverse_lazy("muestras:paso2")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.solicitud = get_or_create_solicitud(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        return {
            "nombre_comercio": self.solicitud.nombre_comercio,
            "giro": self.solicitud.giro,
            "programa_especial": self.solicitud.programa_especial,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "eventos"
        context["step"] = 1
        context["solicitud"] = self.solicitud
        context["evento_nombre"] = EVENTO_NOMBRE
        context["datos_globales"] = _datos_globales(self.request.user)
        return context

    def form_valid(self, form):
        try:
            guardar_paso1(self.solicitud, form.cleaned_data)
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field if field in form.fields else None, err)
            else:
                form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "Datos del comercio guardados.")
        return super().form_valid(form)


class Paso2View(LoginRequiredMixin, FormView):
    template_name = "muestras/paso2.html"
    form_class = Paso2Form
    login_url = "autenticacion:login"
    success_url = reverse_lazy("muestras:listo")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.solicitud = get_or_create_solicitud(request.user)
        if not self.solicitud.paso1_completo:
            messages.info(request, "Completa primero los datos del comercio.")
            return redirect("muestras:paso1")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "eventos"
        context["step"] = 2
        context["solicitud"] = self.solicitud
        context["evento_nombre"] = EVENTO_NOMBRE
        return context

    def form_valid(self, form):
        logo = form.cleaned_data.get("logo")
        imagenes = self.request.FILES.getlist("imagenes")
        if not logo and self.solicitud.logo:
            logo = None
        try:
            if not logo and not self.solicitud.logo:
                form.add_error("logo", "El logo del comercio es obligatorio.")
                return self.form_invalid(form)
            if not imagenes and not self.solicitud.imagenes.exists():
                form.add_error("imagenes", "Sube al menos una imagen del comercio.")
                return self.form_invalid(form)
            guardar_paso2(self.solicitud, logo=logo, imagenes=imagenes or None)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, "Archivos del comercio guardados.")
        return super().form_valid(form)


class ListoView(LoginRequiredMixin, TemplateView):
    template_name = "muestras/listo.html"
    login_url = "autenticacion:login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.solicitud = get_or_create_solicitud(request.user)
        if not self.solicitud.paso1_completo or not self.solicitud.paso2_completo:
            return redirect("muestras:paso1" if not self.solicitud.paso1_completo else "muestras:paso2")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "eventos"
        context["solicitud"] = self.solicitud
        context["evento_nombre"] = EVENTO_NOMBRE
        return context
