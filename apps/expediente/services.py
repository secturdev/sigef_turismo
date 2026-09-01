from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from .models import (
    CampoAdicional,
    DatosGenerales,
    Documento,
    Expediente,
    TipoDocumento,
    ValorCampoAdicional,
    VersionDocumento,
)
from .validators import (
    normalize_upper,
    validate_curp,
    validate_document_file,
    validate_telefono,
)

DIAS_POR_VENCER = 30

ESTADO_VIGENTE = "VIGENTE"
ESTADO_POR_VENCER = "POR_VENCER"
ESTADO_VENCIDO = "VENCIDO"
ESTADO_SIN_FECHA = "SIN_FECHA"


def get_or_create_expediente(usuario) -> Expediente:
    expediente, _ = Expediente.objects.get_or_create(usuario=usuario)
    return expediente


def set_tipo_persona(expediente: Expediente, tipo_persona: str) -> Expediente:
    if tipo_persona not in Expediente.TipoPersona.values:
        raise ValidationError("Tipo de persona no válido.")
    expediente.tipo_persona = tipo_persona
    expediente.save(update_fields=["tipo_persona", "fecha_actualizacion"])
    return expediente


def _required_general_fields(tipo_persona: str) -> set[str]:
    if tipo_persona == Expediente.TipoPersona.PERSONA_FISICA:
        return {
            "nombres",
            "apellido_paterno",
            "apellido_materno",
            "curp",
            "telefono",
            "correo_contacto",
        }
    if tipo_persona == Expediente.TipoPersona.PERSONA_MORAL:
        return {"nombres", "representante_legal", "curp"}
    if tipo_persona == Expediente.TipoPersona.CIUDADANO:
        return {
            "nombres",
            "apellido_paterno",
            "apellido_materno",
            "curp",
            "telefono",
            "correo_contacto",
        }
    return set()


_FIXED_GENERAL_FIELDS = (
    "nombres",
    "apellido_paterno",
    "apellido_materno",
    "curp",
    "rfc",
    "telefono",
    "correo_contacto",
    "domicilio",
    "representante_legal",
)


def update_datos_generales(expediente: Expediente, data: dict[str, Any]) -> DatosGenerales:
    if not expediente.tipo_persona:
        raise ValidationError("Selecciona primero el tipo de persona.")

    tipo = expediente.tipo_persona
    required = _required_general_fields(tipo)
    cleaned: dict[str, str] = {}

    for field in _FIXED_GENERAL_FIELDS:
        cleaned[field] = (data.get(field) or "").strip()

    labels = {
        "nombres": "Nombres / razón social",
        "apellido_paterno": "Apellido paterno",
        "apellido_materno": "Apellido materno",
        "curp": (
            "CURP del representante legal"
            if tipo == Expediente.TipoPersona.PERSONA_MORAL
            else "CURP"
        ),
        "rfc": "RFC",
        "telefono": "Número de celular",
        "correo_contacto": "Correo electrónico",
        "domicilio": "Domicilio",
        "representante_legal": "Nombre del representante legal",
    }

    for field in required:
        if not cleaned[field]:
            raise ValidationError({field: f"{labels[field]} es obligatorio."})

    cleaned["curp"] = validate_curp(cleaned["curp"])
    if cleaned["telefono"]:
        cleaned["telefono"] = validate_telefono(cleaned["telefono"])
    cleaned["rfc"] = normalize_upper(cleaned["rfc"]) if cleaned["rfc"] else ""
    cleaned["domicilio"] = cleaned["domicilio"]

    if tipo != Expediente.TipoPersona.PERSONA_MORAL:
        cleaned["representante_legal"] = ""
    if tipo == Expediente.TipoPersona.PERSONA_MORAL:
        cleaned["apellido_paterno"] = ""
        cleaned["apellido_materno"] = ""

    datos, _ = DatosGenerales.objects.update_or_create(
        expediente=expediente,
        defaults=cleaned,
    )
    expediente.save(update_fields=["fecha_actualizacion"])
    return datos


def save_additional_fields(
    expediente: Expediente,
    values_by_clave: dict[str, Any],
) -> list[ValorCampoAdicional]:
    if not expediente.tipo_persona:
        raise ValidationError("Selecciona primero el tipo de persona.")

    campos = CampoAdicional.objects.filter(activo=True)
    saved: list[ValorCampoAdicional] = []

    for campo in campos:
        tipos = campo.tipos_persona or []
        if tipos and expediente.tipo_persona not in tipos:
            continue

        raw = values_by_clave.get(campo.clave)
        if campo.obligatorio and (raw is None or raw == ""):
            raise ValidationError({campo.clave: f"{campo.etiqueta} es obligatorio."})

        valor, _ = ValorCampoAdicional.objects.update_or_create(
            expediente=expediente,
            campo=campo,
            defaults={"valor": raw},
        )
        saved.append(valor)

    expediente.save(update_fields=["fecha_actualizacion"])
    return saved


def _file_sha256(uploaded: UploadedFile) -> str:
    digest = hashlib.sha256()
    for chunk in uploaded.chunks():
        digest.update(chunk)
    uploaded.seek(0)
    return digest.hexdigest()


def _resolve_vencimiento(
    tipo: TipoDocumento,
    fecha_emision: date | None,
    fecha_vencimiento: date | None,
) -> date | None:
    if fecha_vencimiento:
        return fecha_vencimiento
    if fecha_emision and tipo.dias_vigencia:
        return fecha_emision + timedelta(days=tipo.dias_vigencia)
    return None


@transaction.atomic
def upload_document_version(
    expediente: Expediente,
    tipo_documento: TipoDocumento,
    uploaded: UploadedFile,
    *,
    fecha_emision: date | None = None,
    fecha_vencimiento: date | None = None,
    usuario=None,
) -> VersionDocumento:
    assert_expediente_owner(expediente, usuario)

    if not tipo_documento.activo:
        raise ValidationError("Este tipo de documento no está disponible.")

    validate_document_file(uploaded)
    hash_value = _file_sha256(uploaded)
    vencimiento = _resolve_vencimiento(tipo_documento, fecha_emision, fecha_vencimiento)

    documento, _ = Documento.objects.get_or_create(
        expediente=expediente,
        tipo_documento=tipo_documento,
    )

    version = VersionDocumento(
        documento=documento,
        nombre_original=uploaded.name or "archivo",
        fecha_emision=fecha_emision,
        fecha_vencimiento=vencimiento,
        hash_sha256=hash_value,
    )
    version.archivo = uploaded
    version.save()

    documento.version_actual = version
    documento.save(update_fields=["version_actual"])
    expediente.save(update_fields=["fecha_actualizacion"])
    return version


def assert_expediente_owner(expediente: Expediente, usuario) -> None:
    if usuario is None:
        return
    if expediente.usuario_id != usuario.id:
        raise PermissionDenied("No tienes acceso a este expediente.")


def assert_document_owner(documento: Documento, usuario) -> None:
    if documento.expediente.usuario_id != usuario.id:
        raise PermissionDenied("No tienes acceso a este documento.")


def calculate_document_status(
    version: VersionDocumento | None,
    *,
    today: date | None = None,
) -> str:
    if version is None or not version.fecha_vencimiento:
        return ESTADO_SIN_FECHA

    hoy = today or timezone.localdate()
    if version.fecha_vencimiento < hoy:
        return ESTADO_VENCIDO
    if version.fecha_vencimiento <= hoy + timedelta(days=DIAS_POR_VENCER):
        return ESTADO_POR_VENCER
    return ESTADO_VIGENTE


def _datos_completos(expediente: Expediente) -> bool:
    if not expediente.tipo_persona:
        return False
    try:
        datos = expediente.datos_generales
    except DatosGenerales.DoesNotExist:
        return False

    required = _required_general_fields(expediente.tipo_persona)
    for field in required:
        if not getattr(datos, field, ""):
            return False

    # Campos adicionales obligatorios aplicables al tipo.
    for campo in CampoAdicional.objects.filter(activo=True, obligatorio=True):
        tipos = campo.tipos_persona or []
        if tipos and expediente.tipo_persona not in tipos:
            continue
        valor = (
            ValorCampoAdicional.objects.filter(expediente=expediente, campo=campo)
            .values_list("valor", flat=True)
            .first()
        )
        if valor is None or valor == "":
            return False
    return True


def _documentos_requeridos(expediente: Expediente | None = None) -> list[TipoDocumento]:
    qs = TipoDocumento.objects.filter(activo=True)
    if expediente is None or not expediente.tipo_persona:
        return list(qs)
    tipos: list[TipoDocumento] = []
    for tipo in qs:
        if tipo.aplica_a(expediente.tipo_persona):
            tipos.append(tipo)
    return tipos


def calculate_expediente_progress(expediente: Expediente) -> dict[str, Any]:
    tipos = _documentos_requeridos(expediente)
    tipos_obligatorios = [tipo for tipo in tipos if tipo.obligatorio]
    total = 1 + 1 + len(tipos_obligatorios)
    done = 0

    has_tipo = bool(expediente.tipo_persona)
    if has_tipo:
        done += 1

    has_datos = _datos_completos(expediente)
    if has_datos:
        done += 1

    docs_status: list[dict[str, Any]] = []
    for tipo in tipos:
        documento = (
            Documento.objects.filter(expediente=expediente, tipo_documento=tipo)
            .select_related("version_actual")
            .first()
        )
        version = documento.version_actual if documento else None
        if version and tipo.obligatorio:
            done += 1
        docs_status.append(
            {
                "tipo": tipo,
                "documento": documento,
                "version": version,
                "estado": calculate_document_status(version),
                "cargado": version is not None,
                "obligatorio": tipo.obligatorio,
            }
        )

    percent = int(round((done / total) * 100)) if total else 0
    return {
        "percent": percent,
        "done": done,
        "total": total,
        "has_tipo_persona": has_tipo,
        "has_datos_generales": has_datos,
        "documentos": docs_status,
        "is_complete": done == total and total > 0,
        "next_step": _next_step(has_tipo, has_datos, docs_status),
    }


def _next_step(has_tipo: bool, has_datos: bool, docs_status: list[dict]) -> str | None:
    if not has_tipo:
        return "person_type"
    if not has_datos:
        return "general_data"
    for item in docs_status:
        if item["obligatorio"] and not item["cargado"]:
            return "documents"
    return None
