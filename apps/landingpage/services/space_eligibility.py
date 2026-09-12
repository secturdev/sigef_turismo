from __future__ import annotations

from collections.abc import Iterable

from apps.landingpage.boletab import get_boletab_places
from apps.landingpage.models import Evento, ReglaEspacio
from apps.muestras.models import SolicitudMuestra


def _matches_giro(rule: ReglaEspacio, solicitud: SolicitudMuestra) -> bool:
    return any(
        item.get("giro") == solicitud.giro
        and (not item.get("subgiro") or item.get("subgiro") == solicitud.subgiro)
        for item in rule.reglas
    )


def _matches_folio(rule: ReglaEspacio, folio: str) -> bool:
    return folio in rule.folios


def _serialize_place(
    place: dict, boletab_event_id: str, access_type: str, section_capacity=None
) -> dict:
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
    if section_capacity is not None:
        result["capacidad_seccion"] = section_capacity
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

    rules: Iterable[ReglaEspacio] = event.reglas_espacios.all()
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

    explicit_rules = {
        (rule.boletab_evento_id, rule.asiento_id) for rule in all_rules
    }
    section_capacities = {}
    if not uses_folio:
        for section_rule in event.reglas_secciones.all():
            for item in section_rule.reglas:
                if (
                    item.get("giro") == solicitud.giro
                    and item.get("subgiro") == solicitud.subgiro
                ):
                    section_capacities[
                        (section_rule.boletab_evento_id, section_rule.seccion_id)
                    ] = item["cantidad"]

    result = []
    for linked_event in event.boletab_eventos:
        boletab_event_id = str(linked_event["id"])
        allowed_ids = rules_by_event.get(boletab_event_id, set())
        has_section_rules = any(key[0] == boletab_event_id for key in section_capacities)
        if not allowed_ids and not has_section_rules:
            continue
        for place in get_boletab_places(boletab_event_id):
            asiento_id = str(place.get("asientoId"))
            section_key = (boletab_event_id, str(place.get("seccionId")))
            has_explicit_rule = (boletab_event_id, asiento_id) in explicit_rules
            allowed_by_space = asiento_id in allowed_ids
            allowed_by_section = not has_explicit_rule and section_key in section_capacities
            if not allowed_by_space and not allowed_by_section:
                continue
            if place.get("estado") != "DISPONIBLE" or not place.get("habilitado"):
                continue
            result.append(
                _serialize_place(
                    place,
                    boletab_event_id,
                    access_type,
                    section_capacities.get(section_key) if allowed_by_section else None,
                )
            )

    return access_type, folio if uses_folio else None, valid_folio, result
