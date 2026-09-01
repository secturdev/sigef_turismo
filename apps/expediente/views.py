from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import FormView, TemplateView

from .forms import CommerceForm, DocumentUploadForm, FurnitureForm, GeneralDataForm, PersonTypeForm, ProductForm
from .models import Comercio, Mobiliario, Producto, TipoDocumento, VersionDocumento
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
                error_tipo_id=None, product_form=None, editing_product=None,
                furniture_form=None, editing_furniture=None, commerce_form=None):
        progress = calculate_expediente_progress(self.expediente)
        for item in progress["documentos"]:
            prefix = f"doc-{item['tipo'].pk}"
            item["upload_form"] = (
                upload_form
                if error_tipo_id == item["tipo"].pk and upload_form is not None
                else DocumentUploadForm(prefix=prefix)
            )
        commerce = Comercio.objects.filter(expediente=self.expediente).first()
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
                "products": self.expediente.productos.all(),
                "product_form": product_form or ProductForm(instance=editing_product),
                "editing_product": editing_product,
                "furniture": self.expediente.mobiliario.all(),
                "furniture_form": furniture_form or FurnitureForm(instance=editing_furniture),
                "editing_furniture": editing_furniture,
                "commerce": commerce,
                "commerce_form": commerce_form or CommerceForm(instance=commerce),
                "nav_active": "expediente",
            },
        )

    def get(self, request):
        tab = request.GET.get("tab")
        active_tab = tab if tab in {"comercio", "documents", "products", "mobiliario"} else "general"
        editing_product = None
        if active_tab == "products" and request.GET.get("edit_product"):
            editing_product = get_object_or_404(
                Producto,
                pk=request.GET["edit_product"],
                expediente=self.expediente,
            )
        editing_furniture = None
        if active_tab == "mobiliario" and request.GET.get("edit_furniture"):
            editing_furniture = get_object_or_404(
                Mobiliario, pk=request.GET["edit_furniture"], expediente=self.expediente
            )
        return self._render(
            active_tab=active_tab,
            editing_product=editing_product,
            editing_furniture=editing_furniture,
        )

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

        if action == "add_product":
            form = ProductForm(request.POST, request.FILES)
            if not form.is_valid():
                return self._render(active_tab="products", product_form=form)
            with transaction.atomic():
                product = form.save(commit=False)
                product.expediente = self.expediente
                if product.es_principal:
                    self.expediente.productos.filter(es_principal=True).update(
                        es_principal=False
                    )
                product.save()
            messages.success(request, f"Producto «{product.nombre}» agregado al catálogo.")
            return redirect(f"{request.path}?tab=products")

        if action == "edit_product":
            product = get_object_or_404(
                Producto,
                pk=request.POST.get("product_id"),
                expediente=self.expediente,
            )
            form = ProductForm(request.POST, request.FILES, instance=product)
            if not form.is_valid():
                return self._render(
                    active_tab="products",
                    product_form=form,
                    editing_product=product,
                )
            with transaction.atomic():
                updated = form.save(commit=False)
                if updated.es_principal:
                    self.expediente.productos.filter(es_principal=True).exclude(
                        pk=updated.pk
                    ).update(es_principal=False)
                updated.save()
            messages.success(request, f"Producto «{updated.nombre}» actualizado.")
            return redirect(f"{request.path}?tab=products")

        if action == "delete_product":
            product = get_object_or_404(
                Producto,
                pk=request.POST.get("product_id"),
                expediente=self.expediente,
            )
            product_name = product.nombre
            files = [product.imagen, product.factura]
            product.delete()
            for stored_file in files:
                if stored_file and stored_file.name:
                    stored_file.storage.delete(stored_file.name)
            messages.success(request, f"Producto «{product_name}» eliminado.")
            return redirect(f"{request.path}?tab=products")

        if action in {"add_furniture", "edit_furniture"}:
            furniture = None
            if action == "edit_furniture":
                furniture = get_object_or_404(
                    Mobiliario,
                    pk=request.POST.get("furniture_id"),
                    expediente=self.expediente,
                )
            form = FurnitureForm(request.POST, request.FILES, instance=furniture)
            if not form.is_valid():
                return self._render(
                    active_tab="mobiliario",
                    furniture_form=form,
                    editing_furniture=furniture,
                )
            saved = form.save(commit=False)
            saved.expediente = self.expediente
            saved.save()
            messages.success(request, f"Mobiliario «{saved.nombre}» guardado.")
            return redirect(f"{request.path}?tab=mobiliario")

        if action == "delete_furniture":
            furniture = get_object_or_404(
                Mobiliario,
                pk=request.POST.get("furniture_id"),
                expediente=self.expediente,
            )
            name = furniture.nombre
            files = [furniture.imagen, furniture.factura]
            furniture.delete()
            for stored_file in files:
                if stored_file and stored_file.name:
                    stored_file.storage.delete(stored_file.name)
            messages.success(request, f"Mobiliario «{name}» eliminado.")
            return redirect(f"{request.path}?tab=mobiliario")

        if action == "save_commerce":
            commerce = Comercio.objects.filter(expediente=self.expediente).first()
            form = CommerceForm(request.POST, request.FILES, instance=commerce)
            if not form.is_valid():
                return self._render(active_tab="comercio", commerce_form=form)
            saved = form.save(commit=False)
            saved.expediente = self.expediente
            saved.save()
            messages.success(request, "Información del comercio guardada.")
            return redirect(f"{request.path}?tab=comercio")

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


@login_required(login_url="autenticacion:login")
def product_image(request, product_id: int):
    product = get_object_or_404(Producto, pk=product_id, expediente__usuario=request.user)
    if not product.imagen:
        raise Http404("Imagen no encontrada.")
    return FileResponse(product.imagen.open("rb"), filename=product.imagen.name.rsplit("/", 1)[-1])


@login_required(login_url="autenticacion:login")
def product_invoice(request, product_id: int):
    product = get_object_or_404(Producto, pk=product_id, expediente__usuario=request.user)
    if not product.factura:
        raise Http404("Factura no encontrada.")
    return FileResponse(
        product.factura.open("rb"),
        as_attachment=True,
        filename=product.factura.name.rsplit("/", 1)[-1],
    )


@login_required(login_url="autenticacion:login")
def furniture_file(request, furniture_id: int, file_type: str):
    furniture = get_object_or_404(
        Mobiliario, pk=furniture_id, expediente__usuario=request.user
    )
    stored_file = furniture.imagen if file_type == "imagen" else furniture.factura
    if not stored_file:
        raise Http404("Archivo no encontrado.")
    return FileResponse(
        stored_file.open("rb"),
        as_attachment=file_type == "factura",
        filename=stored_file.name.rsplit("/", 1)[-1],
    )


@login_required(login_url="autenticacion:login")
def commerce_logo(request):
    commerce = get_object_or_404(Comercio, expediente__usuario=request.user)
    return FileResponse(
        commerce.logo.open("rb"), filename=commerce.logo.name.rsplit("/", 1)[-1]
    )
