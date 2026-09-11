from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import SuspiciousOperation
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

from .forms import AdminCreateForm, AdminLoginForm, EventCreateForm, SpaceRuleForm
from .models import Usuario
from apps.landingpage.models import Evento, ReglaEspacio
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
            except BoletabError as exc:
                messages.error(self.request, str(exc))
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
        catalog = self.event.catalogo_giros
        context["rule_form"] = SpaceRuleForm(catalog=catalog or None)
        context["rule_catalog"] = ({
            "giros": [{"id": giro["id"], "name": giro["nombre"]} for giro in catalog],
            "subgiros": {giro["id"]: [{"id": item["id"], "name": item["nombre"]} for item in giro["subgiros"]] for giro in catalog},
        } if catalog else {
            "giros": [{"id": value, "name": label} for value, label in GIROS],
            "subgiros": {giro: [{"id": value, "name": label} for value, label in choices] for giro, choices in SUBGIROS_POR_GIRO.items()},
        })
        return context

    def post(self, request, *args, **kwargs):
        linked_ids = {item["id"] for item in self.event.boletab_eventos}
        form = SpaceRuleForm(request.POST, catalog=self.event.catalogo_giros or None)
        if not form.is_valid():
            messages.error(request, "Revisa la configuración del espacio.")
            return self.get(request, *args, **kwargs)

        data = form.cleaned_data
        if data["boletab_evento_id"] not in linked_ids:
            messages.error(request, "El evento de Boletab no está vinculado.")
            return redirect("autenticacion:admin_events")

        try:
            places = get_boletab_places(data["boletab_evento_id"])
        except BoletabError as exc:
            messages.error(request, str(exc))
            return redirect(
                f"{request.path}?{urlencode({'evento': data['boletab_evento_id']})}"
            )
        valid_places = {str(place.get("asientoId")): place for place in places}
        if data["asiento_id"] not in valid_places:
            messages.error(request, "El espacio seleccionado no pertenece al evento.")
            return redirect("autenticacion:admin_events")

        place = valid_places[data["asiento_id"]]
        ReglaEspacio.objects.update_or_create(
            evento=self.event,
            boletab_evento_id=data["boletab_evento_id"],
            asiento_id=data["asiento_id"],
            defaults={
                "etiqueta": place.get("etiqueta") or data["etiqueta"],
                "reglas": data["reglas_json"],
                "giros": list(dict.fromkeys(r["giro"] for r in data["reglas_json"])),
                "subgiros": list(
                    dict.fromkeys(
                        r["subgiro"] for r in data["reglas_json"] if r["subgiro"]
                    )
                ),
                "folios": data["folios"],
            },
        )
        messages.success(request, f"Se guardaron las reglas de {place.get('etiqueta')}.")
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
        return JsonResponse({"sections": sections})


class AdminLogoutView(LogoutView):
    next_page = "autenticacion:admin_login"


class UserLogoutView(OIDCLogoutView):
    pass


class LlaveTabascoStartView(View):
    def get(self, request):
        return redirect("oidc_authentication_init")
