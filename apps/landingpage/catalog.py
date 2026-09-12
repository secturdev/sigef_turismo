from __future__ import annotations

from django.urls import reverse

from .models import Evento

def build_event_cards() -> list[dict]:
    return [
        {
            "id": event.pk,
            "title": event.nombre,
            "description": event.descripcion,
            "image_url": event.imagen.url,
            "url": f"{reverse('muestras:paso1')}?evento={event.pk}",
            "register_url": f"{reverse('muestras:paso1')}?evento={event.pk}",
            "disponible": True,
        }
        for event in Evento.objects.filter(visible=True).order_by("-fecha_registro")
    ]
