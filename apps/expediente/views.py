from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import DocumentUploadForm, GeneralDataForm, PersonTypeForm
from .models import TipoDocumento, VersionDocumento
from .services import (
    assert_document_owner,
    calculate_expediente_progress,
    get_or_create_expediente,
    save_additional_fields,
    set_tipo_persona,
    update_datos_generales,
    upload_document_version,
)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "expediente/dashboard.html"
    login_url = "autenticacion:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expediente = get_or_create_expediente(self.request.user)
        context["expediente"] = expediente
        context["progress"] = calculate_expediente_progress(expediente)
        context["nav_active"] = "dashboard"
        return context


class EventsView(LoginRequiredMixin, TemplateView):
    template_name = "expediente/events.html"
    login_url = "autenticacion:login"

    def get_context_data(self, **kwargs):
        from apps.landingpage.catalog import build_event_cards

        context = super().get_context_data(**kwargs)
        context["event_cards"] = build_event_cards()
        context["nav_active"] = "eventos"
        return context


class PersonTypeView(LoginRequiredMixin, FormView):
    template_name = "expediente/wizard/person_type.html"
    form_class = PersonTypeForm
    login_url = "autenticacion:login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.expediente = get_or_create_expediente(request.user)
        return FormView.dispatch(self, request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.expediente.tipo_persona:
            initial["tipo_persona"] = self.expediente.tipo_persona
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["identidad_oidc"] = bool(self.request.user.oidc_sub)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["expediente"] = self.expediente
        context["nav_active"] = "expediente"
        context["step"] = 1
        context["identidad_oidc"] = bool(self.request.user.oidc_sub)
        return context


class ProfileView(LoginRequiredMixin, View):
    template_name = "expediente/profile.html"
    login_url = "autenticacion:login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.expediente = get_or_create_expediente(request.user)
        if not self.expediente.tipo_persona:
            messages.info(request, "Selecciona primero el tipo de persona.")
            return redirect("expediente:person_type")
        return View.dispatch(self, request, *args, **kwargs)

    def _general_initial(self):
        initial = {}
        if hasattr(self.expediente, "datos_generales"):
            datos = self.expediente.datos_generales
            for field in (
                "nombres", "apellido_paterno", "apellido_materno", "curp",
                "telefono", "correo_contacto", "representante_legal",
            ):
                initial[field] = getattr(datos, field)
        for valor in self.expediente.valores_adicionales.select_related("campo"):
            initial[f"extra_{valor.campo.clave}"] = valor.valor or ""
        return initial

    def _general_form(self, data=None):
        return GeneralDataForm(
            data=data,
            initial=self._general_initial(),
            tipo_persona=self.expediente.tipo_persona,
            identidad_oidc=bool(self.request.user.oidc_sub),
        )

    def _render(self, *, active_tab="general", general_form=None, upload_form=None,
                error_tipo_id=None):
        progress = calculate_expediente_progress(self.expediente)
        for item in progress["documentos"]:
            prefix = f"doc-{item['tipo'].pk}"
            item["upload_form"] = (
                upload_form
                if error_tipo_id == item["tipo"].pk and upload_form is not None
                else DocumentUploadForm(prefix=prefix)
            )
        return render(
            self.request,
            self.template_name,
            {
                "expediente": self.expediente,
                "progress": progress,
                "general_form": general_form or self._general_form(),
                "upload_form": upload_form or DocumentUploadForm(),
                "error_tipo_id": error_tipo_id,
                "active_tab": active_tab,
                "nav_active": "expediente",
            },
        )

    def get(self, request):
        tab = request.GET.get("tab")
        return self._render(active_tab="documents" if tab == "documents" else "general")

    def post(self, request):
        action = request.POST.get("action")
        if action == "save_general":
            form = self._general_form(request.POST)
            if not form.is_valid():
                return self._render(active_tab="general", general_form=form)
            update_datos_generales(self.expediente, form.cleaned_data)
            save_additional_fields(self.expediente, form.extras_cleaned())
            messages.success(request, "Datos generales guardados.")
            return redirect("expediente:profile")

        if action == "upload_document":
            tipo = get_object_or_404(
                TipoDocumento, pk=request.POST.get("tipo_documento_id"), activo=True
            )
            if not tipo.aplica_a(self.expediente.tipo_persona):
                messages.error(request, "Este documento no aplica a tu tipo de persona.")
                return redirect(f"{request.path}?tab=documents")
            form = DocumentUploadForm(
                request.POST, request.FILES, prefix=f"doc-{tipo.pk}"
            )
            if not form.is_valid():
                return self._render(
                    active_tab="documents", upload_form=form, error_tipo_id=tipo.pk
                )
            upload_document_version(
                self.expediente,
                tipo,
                form.cleaned_data["archivo"],
                fecha_emision=form.cleaned_data.get("fecha_emision"),
                fecha_vencimiento=form.cleaned_data.get("fecha_vencimiento"),
                usuario=request.user,
            )
            messages.success(request, f"Documento «{tipo.nombre}» actualizado.")
            return redirect(f"{request.path}?tab=documents")

        return redirect("expediente:profile")

    def form_valid(self, form):
        set_tipo_persona(self.expediente, form.cleaned_data["tipo_persona"])
        messages.success(self.request, "Tipo de persona guardado.")
        return redirect("expediente:profile")


class GeneralDataView(LoginRequiredMixin, FormView):
    template_name = "expediente/wizard/general_data.html"
    form_class = GeneralDataForm
    login_url = "autenticacion:login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.expediente = get_or_create_expediente(request.user)
        if not self.expediente.tipo_persona:
            messages.info(request, "Selecciona primero el tipo de persona.")
            return redirect("expediente:person_type")
        return FormView.dispatch(self, request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tipo_persona"] = self.expediente.tipo_persona
        kwargs["identidad_oidc"] = bool(self.request.user.oidc_sub)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self.expediente, "datos_generales"):
            datos = self.expediente.datos_generales
            initial.update(
                {
                    "nombres": datos.nombres,
                    "apellido_paterno": datos.apellido_paterno,
                    "apellido_materno": datos.apellido_materno,
                    "curp": datos.curp,
                    "telefono": datos.telefono,
                    "correo_contacto": datos.correo_contacto,
                    "representante_legal": datos.representante_legal,
                }
            )
        for valor in self.expediente.valores_adicionales.select_related("campo"):
            initial[f"extra_{valor.campo.clave}"] = valor.valor or ""
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["expediente"] = self.expediente
        context["nav_active"] = "expediente"
        context["step"] = 2
        return context

    def form_valid(self, form):
        update_datos_generales(self.expediente, form.cleaned_data)
        save_additional_fields(self.expediente, form.extras_cleaned())
        messages.success(self.request, "Datos generales guardados.")
        return redirect("expediente:profile")


class DocumentsView(LoginRequiredMixin, View):
    template_name = "expediente/wizard/documents.html"
    login_url = "autenticacion:login"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.expediente = get_or_create_expediente(request.user)
        if not self.expediente.tipo_persona:
            return redirect("expediente:person_type")
        return View.dispatch(self, request, *args, **kwargs)

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "expediente": self.expediente,
                "progress": calculate_expediente_progress(self.expediente),
                "upload_form": DocumentUploadForm(),
                "nav_active": "expediente",
                "step": 3,
            },
        )

    def post(self, request):
        tipo = get_object_or_404(
            TipoDocumento, pk=request.POST.get("tipo_documento_id"), activo=True
        )
        if not tipo.aplica_a(self.expediente.tipo_persona):
            messages.error(request, "Este documento no aplica a tu tipo de persona.")
            return redirect("expediente:documents")
        form = DocumentUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "expediente": self.expediente,
                    "progress": calculate_expediente_progress(self.expediente),
                    "upload_form": form,
                    "nav_active": "expediente",
                    "step": 3,
                    "error_tipo_id": tipo.pk,
                },
            )

        upload_document_version(
            self.expediente,
            tipo,
            form.cleaned_data["archivo"],
            fecha_emision=form.cleaned_data.get("fecha_emision"),
            fecha_vencimiento=form.cleaned_data.get("fecha_vencimiento"),
            usuario=request.user,
        )
        messages.success(request, f"Documento «{tipo.nombre}» actualizado.")
        return redirect("expediente:documents")


class SummaryView(LoginRequiredMixin, View):
    login_url = "autenticacion:login"

    def get(self, request, *args, **kwargs):
        return redirect("expediente:dashboard")


@login_required(login_url="autenticacion:login")
def download_document_version(request, version_id: int):
    version = get_object_or_404(
        VersionDocumento.objects.select_related("documento__expediente"),
        pk=version_id,
    )
    try:
        assert_document_owner(version.documento, request.user)
    except PermissionDenied:
        raise

    if not version.archivo:
        raise Http404("Archivo no encontrado.")

    return FileResponse(
        version.archivo.open("rb"),
        as_attachment=True,
        filename=version.nombre_original,
    )
