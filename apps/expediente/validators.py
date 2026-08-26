from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[HM]"
    r"(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)"
    r"[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$",
    re.IGNORECASE,
)

RFC_RE = re.compile(
    r"^([A-ZÑ&]{3,4})\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[A-Z0-9]{3}$",
    re.IGNORECASE,
)

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf"}
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

TELEFONO_RE = re.compile(r"^\+?[\d\s()-]{10,20}$")


def normalize_upper(value: str | None) -> str:
    return (value or "").strip().upper()


def validate_telefono(value: str) -> str:
    telefono = (value or "").strip()
    if not telefono:
        raise ValidationError("El teléfono es obligatorio.", code="required")
    digits = re.sub(r"\D", "", telefono)
    if len(digits) < 10:
        raise ValidationError(
            "El teléfono debe tener al menos 10 dígitos.",
            code="invalid",
        )
    if not TELEFONO_RE.match(telefono):
        raise ValidationError("El teléfono no tiene un formato válido.", code="invalid")
    return telefono


def validate_curp(value: str) -> str:
    curp = normalize_upper(value)
    if not curp:
        raise ValidationError("La CURP es obligatoria.", code="required")
    if not CURP_RE.match(curp):
        raise ValidationError("La CURP no tiene un formato válido.", code="invalid")
    return curp


def validate_rfc(value: str) -> str:
    rfc = normalize_upper(value)
    if not rfc:
        raise ValidationError("El RFC es obligatorio.", code="required")
    if not RFC_RE.match(rfc):
        raise ValidationError("El RFC no tiene un formato válido.", code="invalid")
    return rfc


def validate_document_file(uploaded: UploadedFile) -> None:
    name = (uploaded.name or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            "Solo se permiten archivos PDF.",
            code="invalid_extension",
        )
    if uploaded.size and uploaded.size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError(
            "El archivo no puede superar 10 MB.",
            code="file_too_large",
        )
