from __future__ import annotations

from collections.abc import Iterable
from django.utils import timezone

from apps.landingpage.boletab import get_boletab_places
from apps.landingpage.models import Evento, ReglaEspacio
from apps.muestras.models import SolicitudMuestra


def _reconcile_live_spaces(event: Evento, places_by_event: dict[str, list[dict]]) -> None:
    """Fail closed when a saved stand no longer represents the same Boletab stand."""
    checked_at = timezone.now()
    for rule in event.reglas_espacios.all():
        live_places = {
            str(place.get("asientoId")): place
            for place in places_by_event.get(rule.boletab_evento_id, [])
        }
        place = live_places.get(rule.asiento_id)
        current_section = str(place.get("seccionId") or "") if place else ""
        current_label = str(place.get("etiqueta") or "") if place else ""
        if place is None:
            status = ReglaEspacio.EstadoPlantilla.AUSENTE
        elif rule.boletab_seccion_id and rule.boletab_seccion_id != current_section:
            status = ReglaEspacio.EstadoPlantilla.MODIFICADO
        elif rule.etiqueta and current_label and rule.etiqueta != current_label:
            status = ReglaEspacio.EstadoPlantilla.MODIFICADO
        else:
            status = ReglaEspacio.EstadoPlantilla.VIGENTE
        rule.estado_plantilla = status
        rule.ultima_validacion = checked_at
        rule.save(update_fields=("estado_plantilla", "ultima_validacion"))


def _matches_giro(rule: ReglaEspacio, solicitud: SolicitudMuestra) -> bool:
    return any(
        item.get("giro") == solicitud.giro
        and (not item.get("subgiro") or item.get("subgiro") == solicitud.subgiro)
        for item in rule.reglas
    )


def _matches_folio(rule: ReglaEspacio, folio: str) -> bool:
    return folio in rule.folios


def _serialize_place(place: dict, boletab_event_id: str, access_type: str) -> dict:
    result = {
        "boletab_evento_id": boletab_event_id,
        "asiento_id": str(place.get("asientoId")),
        "etiqueta": place.get("etiqueta") or "",
        "seccion_id": place.get("seccionId"),
        "seccion": place.get("seccionNombre") or "",
        "categoria": place.get("categoriaNombre") or "",
        "fila": place.get("fila") or "",
        "numero": place.get("numero"),
        "precio": place.get("precio"),
        "estado": place.get("estado") or "",
        "habilitado": bool(place.get("habilitado")),
        "tipo_acceso": access_type,
    }
    return result


def available_spaces_for_application(
    event: Evento, solicitud: SolicitudMuestra
) -> tuple[str, str | None, bool | None, list[dict]]:
    """Evalúa una solicitud sin reservar espacios ni consumir su folio."""
    folio = solicitud.folio_programa_social.strip().upper()
    event_folios = {item["codigo"] for item in event.catalogo_folios}
    uses_folio = bool(folio)
    valid_folio = folio in event_folios if uses_folio else None
    access_type = "FOLIO" if uses_folio else "GIRO_SUBGIRO"

    places_by_event = {
        str(linked_event["id"]): get_boletab_places(str(linked_event["id"]))
        for linked_event in event.boletab_eventos
    }
    _reconcile_live_spaces(event, places_by_event)

    rules: Iterable[ReglaEspacio] = event.reglas_espacios.filter(
        estado_plantilla=ReglaEspacio.EstadoPlantilla.VIGENTE
    )
    all_rules = list(rules)
    if uses_folio and valid_folio:
        allowed_rules = [rule for rule in all_rules if _matches_folio(rule, folio)]
    elif uses_folio:
        allowed_rules = []
    else:
        allowed_rules = [rule for rule in all_rules if _matches_giro(rule, solicitud)]

    rules_by_event: dict[str, set[str]] = {}
    for rule in allowed_rules:
        rules_by_event.setdefault(rule.boletab_evento_id, set()).add(rule.asiento_id)

    result = []
    for linked_event in event.boletab_eventos:
        boletab_event_id = str(linked_event["id"])
        allowed_ids = rules_by_event.get(boletab_event_id, set())
        if not allowed_ids:
            continue
        for place in places_by_event.get(boletab_event_id, []):
            asiento_id = str(place.get("asientoId"))
            allowed_by_space = asiento_id in allowed_ids
            if not allowed_by_space:
                continue
            if place.get("estado") != "DISPONIBLE" or not place.get("habilitado"):
                continue
            result.append(
                _serialize_place(place, boletab_event_id, access_type)
            )

    return access_type, folio if uses_folio else None, valid_folio, result
