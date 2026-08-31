from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

import jwt
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import resolve_url
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.utils import absolutify

from apps.expediente.services import get_or_create_expediente
from apps.expediente.models import DatosGenerales

from .models import Usuario

logger = logging.getLogger(__name__)


def _log_oidc_claims(claims) -> None:
    """Registra atributos OIDC para diagnóstico sin exponer tokens o secretos."""
    if not settings.OIDC_LOG_CLAIMS:
        return

    payload_json = json.dumps(
        claims,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    )
    logger.warning("Llave Tabasco - JSON completo del token:\n%s", payload_json)
    
    logger.warning("Llave Tabasco - JSON completo del token:\n%s", claims)

def _sync_expediente_identity(user, claims) -> None:
    """Copia al expediente los atributos de identidad administrados por OIDC."""
    # logger.warning("Usuari",user)
    expediente = get_or_create_expediente(user)
    datos, _ = DatosGenerales.objects.get_or_create(expediente=expediente)
    claim_fields = {
        "nombres": (claims.get("given_name") or "").strip(),
        "apellido_paterno": (claims.get("family_name") or "").strip(),
        "apellido_materno": (claims.get("apellido_materno") or "").strip(),
        "correo_contacto": (claims.get("email") or "").strip().lower(),
    }
    changed_fields = []
    for field, value in claim_fields.items():
        if value and getattr(datos, field) != value:
            setattr(datos, field, value)
            changed_fields.append(field)
    if changed_fields:
        datos.save(update_fields=[*changed_fields, "fecha_actualizacion"])


def provider_logout(request) -> str:
    id_token = request.session.get("oidc_id_token")
    logout_redirect = absolutify(request, resolve_url(settings.LOGOUT_REDIRECT_URL))
    if not id_token or not settings.OIDC_OP_LOGOUT_ENDPOINT:
        return logout_redirect

    params = {
        "id_token_hint": id_token,
        "post_logout_redirect_uri": logout_redirect,
        "client_id": settings.OIDC_RP_CLIENT_ID,
    }
    return f"{settings.OIDC_OP_LOGOUT_ENDPOINT}?{urlencode(params)}"


class LlaveTabascoOIDCBackend(OIDCAuthenticationBackend):
    def _verify_jws(self, payload, key):
        header = jwt.get_unverified_header(payload)
        alg = header.get("alg")
        if not alg:
            raise SuspiciousOperation("No alg value found in header")
        if alg != self.OIDC_RP_SIGN_ALGO:
            raise SuspiciousOperation(
                f"Algoritmo del proveedor {alg!r} distinto de OIDC_RP_SIGN_ALGO."
            )

        leeway = self.get_settings("OIDC_CLOCK_SKEW", 120)
        try:
            return jwt.decode(
                payload,
                key,
                algorithms=alg,
                options={"verify_aud": False},
                leeway=leeway,
            )
        except jwt.ImmatureSignatureError as exc:
            raise SuspiciousOperation(
                "Token OIDC aún no válido (iat). Revisa la hora del equipo."
            ) from exc
        except jwt.DecodeError as exc:
            raise SuspiciousOperation("JWS token verification failed.") from exc

    def filter_users_by_claims(self, claims):
        _log_oidc_claims(claims)
        sub = claims.get("sub")
        if not sub:
            return Usuario.objects.none()
        return Usuario.objects.filter(oidc_sub=sub)

    def create_user(self, claims):
        sub = claims.get("sub")
        if not sub:
            return None

        email = (claims.get("email") or f"{sub}@llave-tabasco.local").lower()
        if Usuario.objects.filter(correo=email).exists():
            email = f"{sub}@llave-tabasco.local"

        user = Usuario(
            correo=email,
            oidc_sub=sub,
            nombre_visible=(claims.get("name") or "")[:150],
        )
        user.set_unusable_password()
        user.save()
        _sync_expediente_identity(user, claims)
        return user

    def update_user(self, user, claims):
        name = (claims.get("name") or "").strip()
        email = (claims.get("email") or "").strip().lower()
        changed_fields = []

        if name and user.nombre_visible != name[:150]:
            user.nombre_visible = name[:150]
            changed_fields.append("nombre_visible")

        if email and user.correo != email:
            email_in_use = Usuario.objects.exclude(pk=user.pk).filter(correo=email).exists()
            if email_in_use:
                logger.warning(
                    "Llave Tabasco no pudo actualizar el correo de sub %s: "
                    "el correo %s ya pertenece a otro usuario.",
                    claims.get("sub"),
                    email,
                )
            else:
                user.correo = email
                changed_fields.append("correo")

        if changed_fields:
            user.save(update_fields=changed_fields)
        _sync_expediente_identity(user, claims)
        return user
