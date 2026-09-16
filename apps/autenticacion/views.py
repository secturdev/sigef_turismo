from __future__ import annotations

import json
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView
from django.contrib.auth.views import LogoutView
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCLogoutView,
)

from .forms import AdminCreateForm, AdminLoginForm, AdminPasswordResetForm, AdminUserUpdateForm, EventCreateForm, SpaceRuleForm
from .models import Usuario
from apps.landingpage.models import Evento, ReglaEspacio
from apps.expediente.models import TipoDocumento
from apps.muestras.constants import GIROS, SUBGIROS, SUBGIROS_POR_GIRO
from apps.muestras.models import SolicitudMuestra
from apps.landingpage.boletab import (
    BoletabError,
    get_boletab_events,
    get_boletab_places,
    get_boletab_sections,
)


def _linked_boletab_ids(event):
    """Return Boletab identifiers in the same format used by HTTP parameters."""
    return {
        str(item.get("id"))
        for item in event.boletab_eventos
        if item.get("id") is not None
    }


def _reconcile_space_rules(event, boletab_event_id, places):
    """Mark saved rules that no longer match Boletab without deleting history."""
    current_places = {str(place.get("asientoId")): place for place in places}
    rules = list(
        ReglaEspacio.objects.filter(
            evento=event, boletab_evento_id=boletab_event_id
        )
    )
    checked_at = timezone.now()
    warnings = []
    for rule in rules:
        place = current_places.get(rule.asiento_id)
        previous_section = rule.boletab_seccion_id
        current_section = str(place.get("seccionId") or "") if place else ""
        current_label = str(place.get("etiqueta") or "") if place else ""

        if place is None:
            status = ReglaEspacio.EstadoPlantilla.AUSENTE
            reason = "El stand ya no aparece en la plantilla de Boletab."
        elif previous_section and previous_section != current_section:
            status = ReglaEspacio.EstadoPlantilla.MODIFICADO
            reason = "El stand cambió de sección en Boletab."
        elif rule.etiqueta and current_label and rule.etiqueta != current_label:
            status = ReglaEspacio.EstadoPlantilla.MODIFICADO
            reason = "El identificador ahora corresponde a una etiqueta diferente."
        else:
            status = ReglaEspacio.EstadoPlantilla.VIGENTE
            reason = ""
            if not rule.boletab_seccion_id:
                rule.boletab_seccion_id = current_section
            if not rule.etiqueta:
                rule.etiqueta = current_label

        rule.estado_plantilla = status
        rule.ultima_validacion = checked_at
        rule.save(
            update_fields=(
                "boletab_seccion_id",
                "etiqueta",
                "estado_plantilla",
                "ultima_validacion",
            )
        )
        if status != ReglaEspacio.EstadoPlantilla.VIGENTE:
            warnings.append(
                {
                    "asiento_id": rule.asiento_id,
                    "etiqueta": rule.etiqueta or f"Stand {rule.asiento_id}",
                    "estado": status,
                    "motivo": reason,
                }
            )
    return warnings


OIDC_STATE_NOT_FOUND = "OIDC callback state not found in session `oidc_states`!"


def _can_manage_events(user):
    return user.is_authenticated and user.is_staff and not user.is_validator


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


class AdminLoginView(FormView):
    template_name = "autenticacion/admin_login.html"
    form_class = AdminLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("autenticacion:admin_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect("autenticacion:admin_dashboard")


class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/admin_dashboard.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_dashboard"
        context["admin_count"] = Usuario.objects.filter(is_staff=True).count()
        context["pending_applications"] = SolicitudMuestra.objects.filter(
            estado=SolicitudMuestra.Estado.EN_REVISION
        ).count()
        return context


class AdminUserListView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/admin_create.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_users"
        all_users = list(Usuario.objects.order_by("-is_superuser", "-is_staff", "-fecha_registro"))
        context["all_users"] = all_users
        context["user_table_items"] = [
            {
                "id": account.pk,
                "email": account.correo,
                "search": f"{account.nombre_visible} {account.correo}".lower(),
            }
            for account in all_users
        ]
        context["users_count"] = Usuario.objects.count()
        context["admins_count"] = Usuario.objects.filter(is_staff=True).count()
        context["validators_count"] = Usuario.objects.filter(is_validator=True).count()
        context["active_count"] = Usuario.objects.filter(is_active=True).count()
        context.setdefault("reset_form", AdminPasswordResetForm())
        context.setdefault("reset_user_id", None)
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")
        target = get_object_or_404(Usuario, pk=request.POST.get("user_id"))
        if action == "reset_password":
            if not target.is_staff:
                messages.error(request, "Solo puedes restablecer contraseñas de administradores.")
                return redirect("autenticacion:admin_users")
            reset_form = AdminPasswordResetForm(request.POST, user=target)
            if reset_form.is_valid():
                target.set_password(reset_form.cleaned_data["password"])
                target.save(update_fields=["password"])
                if target.pk == request.user.pk:
                    update_session_auth_hash(request, target)
                messages.success(request, f"Se actualizó la contraseña de {target.correo}.")
                return redirect("autenticacion:admin_users")
            return self.render_to_response(self.get_context_data(
                reset_form=reset_form, reset_user_id=target.pk
            ))

        if target.is_superuser:
            messages.error(request, "No se puede modificar el rol o estado de un superadministrador.")
            return redirect("autenticacion:admin_users")
        if action == "promote_admin":
            target.is_staff = True
            target.is_validator = False
            target.is_active = True
            target.save(update_fields=["is_staff", "is_validator", "is_active"])
            messages.success(request, f"{target.correo} ahora tiene acceso administrativo.")
        elif action == "remove_admin":
            target.is_staff = False
            target.is_validator = False
            target.save(update_fields=["is_staff", "is_validator"])
            messages.success(request, f"Se retiró el acceso administrativo de {target.correo}.")
        elif action == "set_validator":
            target.is_staff = True
            target.is_validator = True
            target.is_active = True
            target.save(update_fields=["is_staff", "is_validator", "is_active"])
            messages.success(request, f"{target.correo} ahora puede validar solicitudes.")
        elif action == "remove_validator":
            target.is_validator = False
            target.save(update_fields=["is_validator"])
            messages.success(request, f"Se retiró el rol de validador de {target.correo}.")
        elif action == "toggle_active":
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(request, f"Se {'activó' if target.is_active else 'desactivó'} a {target.correo}.")
        else:
            messages.error(request, "La acción solicitada no es válida.")
        return redirect("autenticacion:admin_users")



class AdminUserCreateView(UserPassesTestMixin, FormView):
    template_name = "autenticacion/admin_user_form.html"
    form_class = AdminCreateForm
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"nav_active": "admin_users", "form_title": "Registrar usuario", "submit_label": "Crear usuario", "is_update": False})
        return context

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f"Se dio de alta a {user.correo}.")
        return redirect("autenticacion:admin_users")


class AdminUserUpdateView(UserPassesTestMixin, UpdateView):
    template_name = "autenticacion/admin_user_form.html"
    form_class = AdminUserUpdateForm
    model = Usuario
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        target = self.get_object()
        if target.is_superuser and target.pk != request.user.pk:
            messages.error(request, "No puedes editar otro superadministrador.")
            return redirect("autenticacion:admin_users")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"nav_active": "admin_users", "form_title": "Actualizar usuario", "submit_label": "Guardar cambios", "is_update": True})
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object.is_superuser:
            form.fields["role"].disabled = True
            form.fields["is_active"].disabled = True
        return form

    def form_valid(self, form):
        if self.object.is_superuser:
            form.instance.is_staff = True
            form.instance.is_validator = False
            form.instance.is_active = True
        messages.success(self.request, f"Se actualizó a {form.instance.correo}.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("autenticacion:admin_users")


class ApplicationValidationView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/application_list.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_staff and (
            user.is_validator or user.is_superuser
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_applications"
        context["applications"] = SolicitudMuestra.objects.select_related(
            "usuario", "producto_principal", "validada_por"
        ).prefetch_related(
            "detalle_productos__producto", "detalle_mobiliario__mobiliario", "imagenes"
        ).order_by("-fecha_envio", "-fecha_actualizacion")
        context["status_counts"] = {
            value: SolicitudMuestra.objects.filter(estado=value).count()
            for value, _label in SolicitudMuestra.Estado.choices
        }
        return context

    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(SolicitudMuestra, pk=request.POST.get("application_id"))
        action = request.POST.get("action")
        observations = request.POST.get("observations", "").strip()
        if action not in {"approve", "reject"}:
            messages.error(request, "La acción solicitada no es válida.")
            return redirect("autenticacion:admin_applications")
        if action == "reject" and not observations:
            messages.error(request, "Escribe el motivo para rechazar la solicitud.")
            return redirect("autenticacion:admin_applications")

        solicitud.estado = (
            SolicitudMuestra.Estado.APROBADA
            if action == "approve"
            else SolicitudMuestra.Estado.RECHAZADA
        )
        solicitud.observaciones_validacion = observations
        solicitud.validada_por = request.user
        solicitud.fecha_validacion = timezone.now()
        solicitud.save(update_fields=[
            "estado", "observaciones_validacion", "validada_por",
            "fecha_validacion", "fecha_actualizacion",
        ])
        messages.success(
            request,
            f"La solicitud de {solicitud.nombre_comercio or solicitud.usuario.correo} fue {solicitud.get_estado_display().lower()}.",
        )
        return redirect("autenticacion:admin_applications")


class EventListView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/event_list.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_events"
        events = list(Evento.objects.all())
        context["events"] = events
        context["event_table_items"] = [
            {
                "id": event.pk,
                "search": " ".join(
                    [
                        event.nombre,
                        event.descripcion,
                        *[str(item.get("name") or "") for item in event.boletab_eventos],
                    ]
                ).lower(),
            }
            for event in events
        ]
        return context


class EventCreateView(UserPassesTestMixin, FormView):
    template_name = "autenticacion/event_form.html"
    form_class = EventCreateForm
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_events"
        context["form_title"] = "Crear evento"
        context["form_subtitle"] = "Captura la información del nuevo evento."
        context["submit_label"] = "Crear evento"
        context["is_event_edit"] = False
        context["boletab_events_api_url"] = reverse(
            "autenticacion:admin_boletab_events_data"
        )
        context["selected_boletab_event_ids"] = (
            context["form"]["boletab_eventos"].value() or []
        )
        context["document_type_catalog"] = list(
            TipoDocumento.objects.filter(activo=True).values("id", "nombre", "tipos_persona")
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["boletab_events"] = []
        if self.request.method == "POST":
            try:
                kwargs["boletab_events"] = get_boletab_events()
            except BoletabError as exc:
                messages.error(self.request, str(exc))
        return kwargs

    def form_valid(self, form):
        event = form.save()
        messages.success(self.request, f"Se creó el evento {event.nombre}.")
        return redirect("autenticacion:admin_events")


class EventUpdateView(UserPassesTestMixin, UpdateView):
    model = Evento
    form_class = EventCreateForm
    template_name = "autenticacion/event_form.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_events"
        context["form_title"] = "Editar evento"
        context["form_subtitle"] = "Actualiza la información y visibilidad del evento."
        context["submit_label"] = "Guardar cambios"
        context["is_event_edit"] = True
        context["boletab_events_api_url"] = reverse(
            "autenticacion:admin_boletab_events_data"
        )
        context["selected_boletab_event_ids"] = (
            context["form"]["boletab_eventos"].value() or []
        )
        context["document_type_catalog"] = list(
            TipoDocumento.objects.filter(activo=True).values("id", "nombre", "tipos_persona")
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["boletab_events"] = self.object.boletab_eventos
        if self.request.method == "POST":
            try:
                kwargs["boletab_events"] = get_boletab_events()
            except BoletabError:
                # La edición local usa como respaldo las relaciones ya
                # persistidas cuando Boletab no está disponible.
                pass
        return kwargs

    def form_valid(self, form):
        event = form.save()
        messages.success(self.request, f"Se actualizó el evento {event.nombre}.")
        return redirect("autenticacion:admin_events")


class BoletabEventsDataView(UserPassesTestMixin, View):
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get(self, request):
        try:
            events = get_boletab_events()
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        return JsonResponse({"events": events})


# VISTA DE EVENTOS DE ESPACIOS
class EventSpacesView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/event_spaces.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Evento, pk=kwargs["pk"])
        if not self.event.boletab_eventos:
            messages.warning(
                request,
                "Relaciona primero el evento de SIGEF con al menos un evento de Boletab.",
            )
            return redirect("autenticacion:admin_event_update", pk=self.event.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_events"
        context["event"] = self.event
        linked_events = self.event.boletab_eventos
        allowed_ids = _linked_boletab_ids(self.event)
        selected_id = self.request.GET.get("evento", str(linked_events[0]["id"]))
        if selected_id not in allowed_ids:
            selected_id = str(linked_events[0]["id"])
            messages.warning(self.request, "El evento de Boletab seleccionado no está vinculado.")

        context["selected_boletab_event_id"] = selected_id
        context["spaces_api_url"] = reverse(
            "autenticacion:admin_event_spaces_data", args=[self.event.pk]
        )
        context["sections_api_url"] = reverse(
            "autenticacion:admin_event_sections_data", args=[self.event.pk]
        )
        context["event_update_url"] = reverse(
            "autenticacion:admin_event_update", args=[self.event.pk]
        )
        context["allow_template_simulation"] = settings.DEBUG
        catalog = self.event.catalogo_giros
        context["rule_form"] = SpaceRuleForm(
            catalog=catalog or None, folio_catalog=self.event.catalogo_folios
        )
        context["folio_catalog"] = self.event.catalogo_folios
        context["rule_catalog"] = ({
            "giros": [{"id": giro["id"], "name": giro["nombre"]} for giro in catalog],
            "subgiros": {giro["id"]: [{"id": item["id"], "name": item["nombre"]} for item in giro["subgiros"]] for giro in catalog},
        } if catalog else {
            "giros": [{"id": value, "name": label} for value, label in GIROS],
            "subgiros": {giro: [{"id": value, "name": label} for value, label in choices] for giro, choices in SUBGIROS_POR_GIRO.items()},
        })
        context["rule_catalog"]["folios"] = self.event.catalogo_folios
        return context

    def post(self, request, *args, **kwargs):
        wants_json = request.headers.get("Accept") == "application/json"

        def error_response(message, status=400):
            if wants_json:
                return JsonResponse({"error": message}, status=status)
            messages.error(request, message)
            return self.get(request, *args, **kwargs)

        linked_ids = _linked_boletab_ids(self.event)
        if request.POST.get("action") == "clear_space_rules":
            boletab_event_id = request.POST.get("boletab_evento_id", "")
            if boletab_event_id not in linked_ids:
                return error_response("El evento de Boletab no está vinculado.")
            try:
                asiento_ids = json.loads(request.POST.get("asiento_ids_json", "[]"))
            except (TypeError, json.JSONDecodeError):
                return error_response("Los espacios seleccionados no son válidos.")
            if not isinstance(asiento_ids, list):
                return error_response("Los espacios seleccionados no son válidos.")
            asiento_ids = list(dict.fromkeys(str(value).strip() for value in asiento_ids))
            if not asiento_ids or any(not value for value in asiento_ids):
                return error_response("Selecciona al menos un espacio.")

            deleted_count, _ = ReglaEspacio.objects.filter(
                evento=self.event,
                boletab_evento_id=boletab_event_id,
                asiento_id__in=asiento_ids,
            ).delete()
            message = (
                f"Se quitó la configuración individual de {deleted_count} "
                f"espacio{'s' if deleted_count != 1 else ''}."
            )
            if wants_json:
                return JsonResponse({"message": message, "deleted_count": deleted_count})
            messages.success(request, message)
            return redirect(
                f"{request.path}?{urlencode({'evento': boletab_event_id})}"
            )

        form = SpaceRuleForm(
            request.POST,
            catalog=self.event.catalogo_giros or None,
            folio_catalog=self.event.catalogo_folios,
        )
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return error_response(str(first_error))

        data = form.cleaned_data
        if data["boletab_evento_id"] not in linked_ids:
            return error_response("El evento de Boletab no está vinculado.")

        try:
            places = get_boletab_places(data["boletab_evento_id"])
        except BoletabError as exc:
            if wants_json:
                return JsonResponse({"error": str(exc)}, status=502)
            messages.error(request, str(exc))
            return redirect(
                f"{request.path}?{urlencode({'evento': data['boletab_evento_id']})}"
            )
        valid_places = {str(place.get("asientoId")): place for place in places}
        invalid_ids = [
            value
            for value in data["asiento_ids_json"]
            if value not in valid_places
        ]
        if invalid_ids:
            return error_response("Uno o más espacios no pertenecen al evento.")

        giros = list(dict.fromkeys(rule["giro"] for rule in data["reglas_json"]))
        subgiros = list(
            dict.fromkeys(
                rule["subgiro"]
                for rule in data["reglas_json"]
                if rule["subgiro"]
            )
        )
        with transaction.atomic():
            for asiento_id in data["asiento_ids_json"]:
                place = valid_places[asiento_id]
                ReglaEspacio.objects.update_or_create(
                    evento=self.event,
                    boletab_evento_id=data["boletab_evento_id"],
                    asiento_id=asiento_id,
                    defaults={
                        "etiqueta": place.get("etiqueta") or "",
                        "boletab_seccion_id": str(place.get("seccionId") or ""),
                        "estado_plantilla": ReglaEspacio.EstadoPlantilla.VIGENTE,
                        "ultima_validacion": timezone.now(),
                        "reglas": data["reglas_json"],
                        "giros": giros,
                        "subgiros": subgiros,
                        "folios": data["folios"],
                    },
                )

        saved_count = len(data["asiento_ids_json"])
        message = f"Se guardó la configuración en {saved_count} espacio{'s' if saved_count != 1 else ''}."
        if wants_json:
            return JsonResponse({
                "message": message,
                "saved_count": saved_count,
                "rules": {
                    "reglas": data["reglas_json"],
                    "giros": giros,
                    "subgiros": subgiros,
                    "folios": data["folios"],
                    "configured": True,
                },
            })
        messages.success(request, message)
        return redirect(
            f"{request.path}?{urlencode({'evento': data['boletab_evento_id']})}"
        )


class EventSpacesDataView(UserPassesTestMixin, View):
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get(self, request, pk):
        event = get_object_or_404(Evento, pk=pk)
        linked_ids = _linked_boletab_ids(event)
        boletab_event_id = request.GET.get("evento", "")
        if boletab_event_id not in linked_ids:
            return JsonResponse(
                {"error": "El evento de Boletab no está vinculado."}, status=400
            )

        try:
            all_places = get_boletab_places(boletab_event_id)
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)

        template_warnings = _reconcile_space_rules(event, boletab_event_id, all_places)
        requested_section = request.GET.get("seccion") or ""
        places = (
            [
                place for place in all_places
                if str(place.get("seccionId") or "") == requested_section
            ]
            if requested_section
            else all_places
        )
        rules = {
            rule.asiento_id: rule
            for rule in ReglaEspacio.objects.filter(
                evento=event,
                boletab_evento_id=boletab_event_id,
                estado_plantilla=ReglaEspacio.EstadoPlantilla.VIGENTE,
            )
        }
        configured_count = 0
        for place in places:
            rule = rules.get(str(place.get("asientoId")))
            place["rules"] = {
                "reglas": rule.reglas if rule else [],
                "giros": rule.giros if rule else [],
                "subgiros": rule.subgiros if rule else [],
                "folios": rule.folios if rule else [],
                "configured": rule is not None,
            }
            if rule:
                configured_count += 1

        coordinates = [point for place in places for point in place["coordinates"]]
        if coordinates:
            xs = [point[0] for point in coordinates]
            ys = [point[1] for point in coordinates]
            padding = 30
            view_box = {
                "x": min(xs) - padding,
                "y": min(ys) - padding,
                "width": max(max(xs) - min(xs) + 2 * padding, 100),
                "height": max(max(ys) - min(ys) + 2 * padding, 100),
            }
        else:
            view_box = {"x": 0, "y": 0, "width": 1000, "height": 700}

        return JsonResponse(
            {
                "places": places,
                "configured_count": configured_count,
                "view_box": view_box,
                "template_warnings": template_warnings,
            }
        )


class EventSectionsDataView(UserPassesTestMixin, View):
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return _can_manage_events(self.request.user)

    def get(self, request, pk):
        event = get_object_or_404(Evento, pk=pk)
        boletab_event_id = request.GET.get("evento", "")
        linked_ids = _linked_boletab_ids(event)
        if boletab_event_id not in linked_ids:
            return JsonResponse(
                {"error": "El evento de Boletab no está vinculado."}, status=400
            )
        try:
            sections = get_boletab_sections(boletab_event_id)
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        return JsonResponse({"sections": sections})

    def post(self, request, pk):
        return JsonResponse(
            {"error": "La configuración por sección ya no está disponible. Configura cada stand individualmente."},
            status=405,
        )
        # Código histórico inaccesible; se conserva temporalmente para facilitar
        # la migración de datos existentes antes de retirar el modelo.
        event = get_object_or_404(Evento, pk=pk)
        form = SectionRuleForm(request.POST, catalog=event.catalogo_giros)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({"error": str(first_error)}, status=400)

        data = form.cleaned_data
        linked_ids = _linked_boletab_ids(event)
        if data["boletab_evento_id"] not in linked_ids:
            return JsonResponse({"error": "El evento de Boletab no está vinculado."}, status=400)
        try:
            sections = get_boletab_sections(data["boletab_evento_id"])
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        valid_sections = {str(item["id"]): item for item in sections}
        if data["seccion_id"] not in valid_sections:
            return JsonResponse({"error": "La sección no pertenece al evento."}, status=400)

        try:
            places = get_boletab_places(
                data["boletab_evento_id"], data["seccion_id"]
            )
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        place_ids = {str(place.get("asientoId")) for place in places}
        individual_spaces = ReglaEspacio.objects.filter(
            evento=event,
            boletab_evento_id=data["boletab_evento_id"],
            asiento_id__in=place_ids,
        ).count()
        global_limit = max(len(place_ids) - individual_spaces, 0)
        requested_capacity = sum(item["cantidad"] for item in data["reglas_json"])
        if requested_capacity > global_limit:
            return JsonResponse(
                {
                    "error": (
                        f"La capacidad global solicitada ({requested_capacity}) supera "
                        f"los {global_limit} espacios disponibles de la sección."
                    ),
                    "capacity": {
                        "total_spaces": len(place_ids),
                        "individual_spaces": individual_spaces,
                        "global_limit": global_limit,
                    },
                },
                status=400,
            )

        section = valid_sections[data["seccion_id"]]
        if not data["reglas_json"]:
            ReglaSeccion.objects.filter(
                evento=event,
                boletab_evento_id=data["boletab_evento_id"],
                seccion_id=data["seccion_id"],
            ).delete()
            return JsonResponse(
                {
                    "message": "Se quitó la configuración global de la sección.",
                    "rules": [],
                    "capacity": {
                        "total_spaces": len(place_ids),
                        "individual_spaces": individual_spaces,
                        "global_limit": global_limit,
                        "allocated": 0,
                        "remaining": global_limit,
                    },
                }
            )

        ReglaSeccion.objects.update_or_create(
            evento=event,
            boletab_evento_id=data["boletab_evento_id"],
            seccion_id=data["seccion_id"],
            defaults={
                "seccion_nombre": section.get("nombre") or "",
                "reglas": data["reglas_json"],
            },
        )
        return JsonResponse(
            {
                "message": "Se guardó la capacidad de la sección.",
                "rules": data["reglas_json"],
                "capacity": {
                    "total_spaces": len(place_ids),
                    "individual_spaces": individual_spaces,
                    "global_limit": global_limit,
                    "allocated": requested_capacity,
                    "remaining": global_limit - requested_capacity,
                },
            }
        )


class AdminLogoutView(LogoutView):
    next_page = "autenticacion:admin_login"


class UserLogoutView(OIDCLogoutView):
    pass


class LlaveTabascoStartView(View):
    def get(self, request):
        return redirect("oidc_authentication_init")
