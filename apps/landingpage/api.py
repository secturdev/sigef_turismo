from __future__ import annotations

import secrets

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from apps.landingpage.boletab import BoletabError
from apps.landingpage.models import Evento
from apps.landingpage.services.space_eligibility import available_spaces_for_application
from apps.muestras.models import SolicitudMuestra


class AvailableSpacesApiView(View):
    http_method_names = ["get"]

    def _is_authorized(self, request) -> bool:
        if request.user.is_authenticated and request.user.is_staff:
            return True
        configured_key = settings.SIGEF_SPACES_API_KEY
        provided_key = request.headers.get("X-API-Key", "")
        return bool(
            configured_key
            and provided_key
            and secrets.compare_digest(provided_key, configured_key)
        )

    def get(self, request, event_id: int, user_id: int):
        if not self._is_authorized(request):
            return JsonResponse({"error": "No autorizado."}, status=401)

        try:
            event = Evento.objects.get(pk=event_id)
        except Evento.DoesNotExist:
            return JsonResponse({"error": "El evento no existe."}, status=404)
        try:
            solicitud = SolicitudMuestra.objects.select_related("usuario").get(
                usuario_id=user_id
            )
        except SolicitudMuestra.DoesNotExist:
            return JsonResponse(
                {"error": "El usuario no tiene una solicitud de participación."},
                status=404,
            )

        try:
            access_type, folio, valid_folio, spaces = available_spaces_for_application(
                event, solicitud
            )
        except BoletabError as exc:
            return JsonResponse({"error": str(exc)}, status=502)

        return JsonResponse(
            {
                "evento_id": event.pk,
                "usuario_id": solicitud.usuario_id,
                "solicitud_id": solicitud.pk,
                "criterio": {
                    "tipo": access_type,
                    "giro": solicitud.giro if access_type == "GIRO_SUBGIRO" else None,
                    "subgiro": (
                        solicitud.subgiro if access_type == "GIRO_SUBGIRO" else None
                    ),
                    "folio": folio,
                    "folio_valido": valid_folio,
                },
                "total": len(spaces),
                "espacios": spaces,
            }
        )
