from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .models import ImagenComercio, SolicitudMuestra

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_IMAGENES = 5


def get_or_create_solicitud(usuario) -> SolicitudMuestra:
    solicitud, _ = SolicitudMuestra.objects.get_or_create(usuario=usuario)
    return solicitud


def _validate_image(uploaded: UploadedFile) -> None:
    name = (uploaded.name or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Solo se permiten imágenes JPG, PNG o WEBP.")
    if uploaded.size and uploaded.size > MAX_IMAGE_SIZE:
        raise ValidationError("Cada imagen no puede superar 5 MB.")


def guardar_paso1(solicitud: SolicitudMuestra, data: dict) -> SolicitudMuestra:
    solicitud.nombre_comercio = (data.get("nombre_comercio") or "").strip()
    solicitud.giro = data.get("giro") or ""
    solicitud.programa_especial = data.get("programa_especial") or ""
    if not solicitud.nombre_comercio:
        raise ValidationError({"nombre_comercio": "El nombre de comercio es obligatorio."})
    if not solicitud.giro:
        raise ValidationError({"giro": "Selecciona un giro."})
    if not solicitud.programa_especial:
        raise ValidationError({"programa_especial": "Selecciona un programa especial."})
    solicitud.paso_actual = max(solicitud.paso_actual, 2)
    solicitud.save()
    return solicitud


@transaction.atomic
def guardar_paso2(
    solicitud: SolicitudMuestra,
    *,
    logo: UploadedFile | None = None,
    imagenes: list[UploadedFile] | None = None,
) -> SolicitudMuestra:
    if logo:
        _validate_image(logo)
        solicitud.logo = logo
        solicitud.save(update_fields=["logo", "fecha_actualizacion"])

    nuevas = [f for f in (imagenes or []) if f]
    if nuevas:
        actuales = solicitud.imagenes.count()
        if actuales + len(nuevas) > MAX_IMAGENES:
            raise ValidationError(
                f"Puedes subir máximo {MAX_IMAGENES} imágenes del comercio."
            )
        for uploaded in nuevas:
            _validate_image(uploaded)
            ImagenComercio.objects.create(
                solicitud=solicitud,
                archivo=uploaded,
                nombre_original=uploaded.name or "imagen",
            )

    if not solicitud.logo:
        raise ValidationError({"logo": "El logo del comercio es obligatorio."})
    if not solicitud.imagenes.exists():
        raise ValidationError({"imagenes": "Sube al menos una imagen del comercio."})

    solicitud.paso_actual = max(solicitud.paso_actual, 3)
    solicitud.save(update_fields=["paso_actual", "fecha_actualizacion"])
    return solicitud
