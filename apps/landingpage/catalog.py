from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.urls import reverse

from .models import Evento

EVENT_CARD_TITLES = {
    "CHOCOLATE": "Festival del Chocolate",
    "EXPO NAVIDEÑA": "Expo Navideña",
    "EXPO NAVIDENA": "Expo Navideña",
    "FERIA": "Feria Tabasco",
    "MOTONAUTICA": "Motonáutica",
}


def build_event_cards() -> list[dict]:
    cards = [
        {
            "title": event.nombre,
            "description": event.descripcion,
            "image_url": event.imagen.url,
            "url": "#",
            "register_url": "#",
            "disponible": False,
        }
        for event in Evento.objects.filter(visible=True)
    ]
    cards_dir = Path(settings.BASE_DIR) / "static" / "img" / "others"
    if not cards_dir.is_dir():
        return cards

    for path in sorted(cards_dir.iterdir()):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        stem = path.stem
        disponible = stem.upper() == "CHOCOLATE"
        cards.append(
            {
                "title": EVENT_CARD_TITLES.get(
                    stem.upper(), stem.replace("_", " ").title()
                ),
                "image": f"img/others/{path.name}",
                "image_url": "",
                "url": "#",
                "register_url": reverse("muestras:paso1") if disponible else "#",
                "disponible": disponible,
            }
        )
    return cards
