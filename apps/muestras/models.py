from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from .constants import GIROS, PROGRAMAS_ESPECIALES


def _ruta_logo(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".png"
    return f"muestras/{instance.usuario_id}/logo/{uuid.uuid4().hex}{ext}"


def _ruta_imagen(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".jpg"
    return f"muestras/{instance.solicitud.usuario_id}/imagenes/{uuid.uuid4().hex}{ext}"


class SolicitudMuestra(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitud_muestra",
        verbose_name="usuario",
    )
    nombre_comercio = models.CharField("nombre de comercio", max_length=200, blank=True)
    giro = models.CharField(
        "giro",
        max_length=64,
        choices=GIROS,
        blank=True,
    )
    programa_especial = models.CharField(
        "programa especial",
        max_length=64,
        choices=PROGRAMAS_ESPECIALES,
        blank=True,
    )
    logo = models.FileField(
        "logo del comercio",
        upload_to=_ruta_logo,
        blank=True,
        null=True,
    )
    paso_actual = models.PositiveSmallIntegerField("paso actual", default=1)
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    fecha_actualizacion = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"

    def __str__(self) -> str:
        return self.nombre_comercio or f"Solicitud {self.pk}"

    @property
    def paso1_completo(self) -> bool:
        return bool(self.nombre_comercio and self.giro and self.programa_especial)

    @property
    def paso2_completo(self) -> bool:
        return bool(self.logo) and self.imagenes.exists()


class ImagenComercio(models.Model):
    solicitud = models.ForeignKey(
        SolicitudMuestra,
        on_delete=models.CASCADE,
        related_name="imagenes",
        verbose_name="solicitud",
    )
    archivo = models.FileField("imagen", upload_to=_ruta_imagen)
    nombre_original = models.CharField("nombre original", max_length=255, blank=True)
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)

    class Meta:
        ordering = ["fecha_carga"]
        verbose_name = "imagen del comercio"
        verbose_name_plural = "imágenes del comercio"

    def __str__(self) -> str:
        return self.nombre_original or f"Imagen #{self.pk}"
