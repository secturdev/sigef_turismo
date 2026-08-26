from django.views.generic import TemplateView

from .catalog import build_event_cards


class HomeView(TemplateView):
    template_name = "landingpage/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["slides"] = [
            {
                "title": "Feria Tabasco 2027",
                "subtitle": (
                    "La gran fiesta de Tabasco con cultura, gastronomía, "
                    "arte y espectáculos para todo público."
                ),
                "image": "img/events/feria-tabasco.png",
                "color": "#4a1f6b",
                "url": "#",
                "info_url": "#",
            },
            {
                "title": "Festival del Chocolate Tabasco 2026",
                "subtitle": (
                    "Del cacao al mundo: tradición, sabores y experiencias "
                    "únicas en torno al chocolate tabasqueño."
                ),
                "image": "img/events/festival-chocolate.png",
                "color": "#0e2f38",
                "url": "#",
                "info_url": "#",
            },
        ]
        context["event_cards"] = build_event_cards()
        return context
