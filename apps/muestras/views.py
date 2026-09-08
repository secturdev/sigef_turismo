from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .constants import EVENTO_INFO, EVENTO_NOMBRE
from .forms import Paso1Form, Paso2Form
from .services import get_or_create_solicitud, guardar_paso1, guardar_paso2


def _datos_globales(user):
    from apps.expediente.models import DatosGenerales, Documento, Expediente, TipoDocumento
    from apps.expediente.services import calculate_document_status

    try:
        expediente = user.expediente
    except Expediente.DoesNotExist:
        return None

    try:
        datos = expediente.datos_generales
    except DatosGenerales.DoesNotExist:
        datos = None

    if expediente.tipo_persona == Expediente.TipoPersona.PERSONA_MORAL:
        campos = [
            ("Razón social", getattr(datos, "nombres", "") or "—"),
            ("Representante legal", getattr(datos, "representante_legal", "") or "—"),
            ("CURP del representante legal", getattr(datos, "curp", "") or "—"),
        ]
    else:
        nombre = " ".join(filter(None, [
            getattr(datos, "nombres", ""),
            getattr(datos, "apellido_paterno", ""),
            getattr(datos, "apellido_materno", ""),
        ]))
        campos = [
            ("Nombre completo", nombre or "—"),
            ("CURP", getattr(datos, "curp", "") or "—"),
        ]
    campos.extend([
        ("RFC", getattr(datos, "rfc", "") or "—"),
        ("Número de celular", getattr(datos, "telefono", "") or "—"),
        ("Correo electrónico", getattr(datos, "correo_contacto", "") or user.correo),
        ("Domicilio", getattr(datos, "domicilio", "") or "—"),
    ])
    documentos = []
    for tipo in TipoDocumento.objects.filter(activo=True):
        if expediente.tipo_persona and not tipo.aplica_a(expediente.tipo_persona):
            continue
        documento = Documento.objects.filter(
            expediente=expediente, tipo_documento=tipo
        ).select_related("version_actual").first()
        version = documento.version_actual if documento else None
        estado = calculate_document_status(version) if version else "PENDIENTE"
        etiquetas_estado = {
            "PENDIENTE": "Pendiente",
            "VIGENTE": "Vigente",
            "POR_VENCER": "Por vencer",
            "VENCIDO": "Vencido",
            "SIN_FECHA": "Cargado",
        }
        documentos.append({
            "tipo": tipo,
            "version": version,
            "estado": estado,
            "estado_label": etiquetas_estado[estado],
        })
    cargados = sum(1 for item in documentos if item["version"])
    obligatorios_pendientes = sum(
        1 for item in documentos if item["tipo"].obligatorio and not item["version"]
    )
    return {
        "tipo_persona": expediente.get_tipo_persona_display() if expediente.tipo_persona else "—",
        "campos": campos,
        "documentos": documentos,
        "documentos_total": len(documentos),
        "documentos_cargados": cargados,
        "documentos_porcentaje": round(cargados * 100 / len(documentos)) if documentos else 100,
        "documentos_obligatorios_pendientes": obligatorios_pendientes,
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
            "giro": self.solicitud.giro,
            "subgiro": self.solicitud.subgiro,
            "programa_especial": self.solicitud.programa_especial,
            "folio_programa_social": self.solicitud.folio_programa_social,
            "productos": self.solicitud.productos.all(),
            "mobiliario": self.solicitud.mobiliario.all(),
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["expediente"] = self.request.user.expediente
        kwargs["solicitud"] = self.solicitud
        kwargs["evento_categoria"] = EVENTO_INFO["categoria"]
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "eventos"
        context["step"] = 1
        context["solicitud"] = self.solicitud
        context["evento_nombre"] = EVENTO_NOMBRE
        context["evento_info"] = EVENTO_INFO
        context["datos_globales"] = _datos_globales(self.request.user)
        context["comercio"] = getattr(self.request.user.expediente, "comercio", None)
        return context

    def form_valid(self, form):
        comercio = getattr(self.request.user.expediente, "comercio", None)
        if comercio is None:
            form.add_error(None, "Registra primero la información de tu comercio en Mi perfil.")
            return self.form_invalid(form)
        try:
            productos, mobiliario = form.participation_details()
            guardar_paso1(
                self.solicitud,
                form.cleaned_data,
                nombre_comercio=comercio.nombre,
                productos=productos,
                mobiliario=mobiliario,
            )
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
