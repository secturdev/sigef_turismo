from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect


class OIDCCanonicalOriginMiddleware:
    """Mantiene todo el flujo OIDC en el origen registrado con el proveedor."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.origin = settings.OIDC_CANONICAL_ORIGIN
        self.parsed_origin = urlsplit(self.origin) if self.origin else None

        if self.parsed_origin and (
            self.parsed_origin.scheme not in {"http", "https"}
            or not self.parsed_origin.netloc
            or self.parsed_origin.path
            or self.parsed_origin.query
            or self.parsed_origin.fragment
        ):
            raise ImproperlyConfigured(
                "OIDC_CANONICAL_ORIGIN debe contener solamente esquema y host, "
                "por ejemplo: https://sistema.tabasco.gob.mx"
            )

    def __call__(self, request):
        if self.parsed_origin and request.path.startswith("/oidc/"):
            current_origin = f"{request.scheme}://{request.get_host()}"
            if current_origin.casefold() != self.origin.casefold():
                return HttpResponseRedirect(f"{self.origin}{request.get_full_path()}")

        return self.get_response(request)
