from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class BoletabError(Exception):
    pass


def _label_layout(label: str, points: list[tuple[float, float]], center_y: float):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    words = label.split()
    lines = [label]

    one_line_size = min(6.0, width / max(len(label) * 0.58, 1), height * 0.42)
    if one_line_size < 3.5 and len(words) > 1:
        best_split = min(
            range(1, len(words)),
            key=lambda index: abs(
                len(" ".join(words[:index])) - len(" ".join(words[index:]))
            ),
        )
        lines = [" ".join(words[:best_split]), " ".join(words[best_split:])]

    longest = max(len(line) for line in lines)
    font_size = min(
        6.0,
        width / max(longest * 0.58, 1),
        height / (len(lines) * 1.35),
    )
    font_size = max(font_size, 1.5)
    line_height = font_size * 1.15
    start_y = center_y - ((len(lines) - 1) * line_height / 2)
    return round(font_size, 2), [
        {"text": line, "y": round(start_y + index * line_height, 2)}
        for index, line in enumerate(lines)
    ]


def _event_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "data", "eventos", "content"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise BoletabError("Boletab devolvió un formato de catálogo no reconocido.")


def get_boletab_events() -> list[dict[str, str]]:
    if not settings.BOLETAB_BASE_URL or not settings.BOLETAB_API_KEY:
        raise BoletabError("La integración con Boletab no está configurada.")

    request = Request(
        f"{settings.BOLETAB_BASE_URL}/eventos",
        headers={"X-API-KEY": settings.BOLETAB_API_KEY, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=settings.BOLETAB_TIMEOUT) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise BoletabError(
                "Boletab rechazó el acceso. Verifica la API key y la IP autorizada."
            ) from exc
        raise BoletabError(f"Boletab respondió con el error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BoletabError("No fue posible consultar el catálogo de Boletab.") from exc

    events = []
    for item in _event_list(payload):
        if not isinstance(item, dict):
            continue
        event_id = item.get("id") or item.get("eventoId") or item.get("evento_id")
        name = item.get("nombre") or item.get("name") or item.get("titulo")
        if event_id is not None and name:
            events.append({"id": str(event_id), "name": str(name), "estado": item.get("estado")})
    return events


def get_boletab_sections(event_id: str) -> list[dict]:
    if not settings.BOLETAB_BASE_URL or not settings.BOLETAB_API_KEY:
        raise BoletabError("La integración con Boletab no está configurada.")
    if not str(event_id).isdigit():
        raise BoletabError("El identificador del evento de Boletab no es válido.")

    request = Request(
        f"{settings.BOLETAB_BASE_URL}/eventos/{event_id}/secciones",
        headers={"X-API-KEY": settings.BOLETAB_API_KEY, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=settings.BOLETAB_TIMEOUT) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise BoletabError(
            f"Boletab respondió con el error HTTP {exc.code} al consultar las secciones."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BoletabError("No fue posible consultar las secciones de Boletab.") from exc

    sections = _event_list(payload)
    return [section for section in sections if isinstance(section, dict) and section.get("id") is not None]


def get_boletab_places(event_id: str, section_id: str | None = None) -> list[dict]:
    if not settings.BOLETAB_BASE_URL or not settings.BOLETAB_API_KEY:
        raise BoletabError("La integración con Boletab no está configurada.")
    if not str(event_id).isdigit():
        raise BoletabError("El identificador del evento de Boletab no es válido.")
    if section_id is not None and not str(section_id).isdigit():
        raise BoletabError("El identificador de la sección de Boletab no es válido.")

    base_url = f"{settings.BOLETAB_BASE_URL}/eventos/{event_id}/lugares"
    headers = {"X-API-KEY": settings.BOLETAB_API_KEY, "Accept": "application/json"}
    try:
        query = {"page": 0, "size": 1000}
        if section_id is not None:
            query["seccionId"] = section_id
        request = Request(f"{base_url}?{urlencode(query)}", headers=headers, method="GET")
        with urlopen(request, timeout=settings.BOLETAB_TIMEOUT) as response:
            payload = json.load(response)
        places = _event_list(payload)
        total_pages = int(payload.get("totalPages", 1)) if isinstance(payload, dict) else 1
        for page in range(1, total_pages):
            query["page"] = page
            request = Request(
                f"{base_url}?{urlencode(query)}", headers=headers, method="GET"
            )
            with urlopen(request, timeout=settings.BOLETAB_TIMEOUT) as response:
                places.extend(_event_list(json.load(response)))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise BoletabError(
                "Boletab rechazó el acceso a los lugares del evento."
            ) from exc
        raise BoletabError(f"Boletab respondió con el error HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BoletabError("No fue posible consultar los lugares de Boletab.") from exc

    normalized = []
    coordinate_pattern = re.compile(r"-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?")
    for place in places:
        if not isinstance(place, dict):
            continue
        pairs = coordinate_pattern.findall(str(place.get("pathSvg") or ""))
        if len(pairs) < 3:
            continue
        points = []
        for pair in pairs:
            x, y = (float(value) for value in pair.split(","))
            points.append((x, y))
        color = str(place.get("categoriaColor") or "#3B82F6")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            color = "#3B82F6"
        pos_y = float(place.get("posY") or sum(y for _, y in points) / len(points))
        label = str(place.get("etiqueta") or place.get("numero") or "")
        label_font_size, label_lines = _label_layout(label, points, pos_y)
        normalized.append(
            {
                **place,
                "points": " ".join(f"{x:g},{y:g}" for x, y in points),
                "coordinates": points,
                "color": color,
                "posX": float(place.get("posX") or sum(x for x, _ in points) / len(points)),
                "posY": pos_y,
                "labelFontSize": label_font_size,
                "labelLines": label_lines,
            }
        )
    return normalized
