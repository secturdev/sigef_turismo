from __future__ import annotations

import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView
from django.contrib.auth.views import LogoutView
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCLogoutView,
)

from .forms import AdminCreateForm, AdminLoginForm, EventCreateForm, SectionRuleForm, SpaceRuleForm
from .models import Usuario
from apps.landingpage.models import Evento, ReglaEspacio, ReglaSeccion
from apps.muestras.constants import GIROS, SUBGIROS, SUBGIROS_POR_GIRO
from apps.landingpage.boletab import (
    BoletabError,
    get_boletab_events,
    get_boletab_places,
    get_boletab_sections,
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
        return context


class AdminCreateView(UserPassesTestMixin, FormView):
    template_name = "autenticacion/admin_create.html"
    form_class = AdminCreateForm
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_users"
        context["admin_users"] = Usuario.objects.filter(is_staff=True).order_by(
            "-fecha_registro"
        )
        return context

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f"Se dio de alta a {user.correo}.")
        return redirect("autenticacion:admin_users")


class EventListView(UserPassesTestMixin, TemplateView):
    template_name = "autenticacion/event_list.html"
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = "admin_events"
        context["events"] = Evento.objects.all()
        return context


class EventCreateView(UserPassesTestMixin, FormView):
    template_name = "autenticacion/event_form.html"
    form_class = EventCreateForm
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

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
        return self.request.user.is_authenticated and self.request.user.is_staff

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
        return self.request.user.is_authenticated and self.request.user.is_staff

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
        return self.request.user.is_authenticated and self.request.user.is_staff

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
        allowed_ids = {item["id"] for item in linked_events}
        selected_id = self.request.GET.get("evento", linked_events[0]["id"])
        if selected_id not in allowed_ids:
            selected_id = linked_events[0]["id"]
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

        linked_ids = {item["id"] for item in self.event.boletab_eventos}
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

        existing_individual_ids = set(
            ReglaEspacio.objects.filter(
                evento=self.event,
                boletab_evento_id=data["boletab_evento_id"],
            ).values_list("asiento_id", flat=True)
        )
        places_by_section: dict[str, set[str]] = {}
        for place_id, place in valid_places.items():
            section_id = str(place.get("seccionId") or "")
            places_by_section.setdefault(section_id, set()).add(place_id)
        selected_ids = set(data["asiento_ids_json"])
        selected_sections = {
            str(valid_places[place_id].get("seccionId") or "")
            for place_id in selected_ids
        }
        section_rules = {
            rule.seccion_id: rule
            for rule in ReglaSeccion.objects.filter(
                evento=self.event,
                boletab_evento_id=data["boletab_evento_id"],
                seccion_id__in=selected_sections,
            )
        }
        for section_id, section_rule in section_rules.items():
            section_place_ids = places_by_section.get(section_id, set())
            individual_count = len(
                section_place_ids & (existing_individual_ids | selected_ids)
            )
            global_limit = max(len(section_place_ids) - individual_count, 0)
            allocated = sum(
                int(item.get("cantidad") or 0) for item in section_rule.reglas
            )
            if allocated > global_limit:
                return error_response(
                    "No puedes configurar este stand individualmente porque la "
                    f"sección tiene {allocated} lugares asignados globalmente y, "
                    f"con este cambio, solo quedarían {global_limit}. Reduce primero "
                    "la capacidad global de la sección."
                )

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
                        "reglas": data["reglas_json"],
                        "giros": giros,
                        "subgiros": subgiros,
                        "folios": data["folios"],
                    },
                )

        saved_count = len(data["asiento_ids_json"])
        message = f"Se guardó la configuración en {saved_count} espacio{'s' if saved_count != 1 else ''}."
        if wants_json:
            return JsonResponse({"message": message, "saved_count": saved_count})
        messages.success(request, message)
        return redirect(
            f"{request.path}?{urlencode({'evento': data['boletab_evento_id']})}"
        )


class EventSpacesDataView(UserPassesTestMixin, View):
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get(self, request, pk):
        event = get_object_or_404(Evento, pk=pk)
        linked_ids = {item["id"] for item in event.boletab_eventos}
        boletab_event_id = request.GET.get("evento", "")
        if boletab_event_id not in linked_ids:
            return JsonResponse(
                {"error": "El evento de Boletab no está vinculado."}, status=400
            )

        try:
            places = get_boletab_places(
                boletab_event_id, request.GET.get("seccion") or None
            )
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)

        rules = {
            rule.asiento_id: rule
            for rule in ReglaEspacio.objects.filter(
                evento=event, boletab_evento_id=boletab_event_id
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

        global_capacity = max(len(places) - configured_count, 0)
        section_rule = ReglaSeccion.objects.filter(
            evento=event,
            boletab_evento_id=boletab_event_id,
            seccion_id=request.GET.get("seccion", ""),
        ).first()
        allocated_capacity = sum(
            int(item.get("cantidad") or 0)
            for item in (section_rule.reglas if section_rule else [])
        )

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
                "section_capacity": {
                    "total_spaces": len(places),
                    "individual_spaces": configured_count,
                    "global_limit": global_capacity,
                    "allocated": allocated_capacity,
                    "remaining": max(global_capacity - allocated_capacity, 0),
                },
                "view_box": view_box,
            }
        )


class EventSectionsDataView(UserPassesTestMixin, View):
    login_url = "autenticacion:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def get(self, request, pk):
        event = get_object_or_404(Evento, pk=pk)
        boletab_event_id = request.GET.get("evento", "")
        linked_ids = {item["id"] for item in event.boletab_eventos}
        if boletab_event_id not in linked_ids:
            return JsonResponse(
                {"error": "El evento de Boletab no está vinculado."}, status=400
            )
        try:
            sections = get_boletab_sections(boletab_event_id)
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
        saved_rules = {
            rule.seccion_id: rule.reglas
            for rule in ReglaSeccion.objects.filter(
                evento=event, boletab_evento_id=boletab_event_id
            )
        }
        for section in sections:
            section["capacity_rules"] = saved_rules.get(str(section["id"]), [])
        return JsonResponse({"sections": sections})

    def post(self, request, pk):
        event = get_object_or_404(Evento, pk=pk)
        form = SectionRuleForm(request.POST, catalog=event.catalogo_giros)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({"error": str(first_error)}, status=400)

        data = form.cleaned_data
        linked_ids = {item["id"] for item in event.boletab_eventos}
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
