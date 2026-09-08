from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from .constants import GIROS, PROGRAMAS_ESPECIALES, SUBGIROS


def _ruta_logo(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".png"
    return f"muestras/{instance.usuario_id}/logo/{uuid.uuid4().hex}{ext}"


def _ruta_imagen(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".jpg"
    return f"muestras/{instance.solicitud.usuario_id}/imagenes/{uuid.uuid4().hex}{ext}"


def _ruta_foto_equipamiento(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".jpg"
    return f"muestras/{instance.usuario_id}/equipamiento/{uuid.uuid4().hex}{ext}"


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
    subgiro = models.CharField("subgiro", max_length=64, choices=SUBGIROS, blank=True)
    programa_especial = models.CharField(
        "programa especial",
        max_length=64,
        choices=PROGRAMAS_ESPECIALES,
        blank=True,
    )
    folio_programa_social = models.CharField("folio del programa social", max_length=100, blank=True)
    logo = models.FileField(
        "logo del comercio",
        upload_to=_ruta_logo,
        blank=True,
        null=True,
    )
    productos = models.ManyToManyField(
        "expediente.Producto", blank=True, related_name="solicitudes_muestra"
    )
    producto_principal = models.ForeignKey(
        "expediente.Producto", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="solicitudes_como_principal", verbose_name="producto principal",
    )
    mobiliario = models.ManyToManyField(
        "expediente.Mobiliario", blank=True, related_name="solicitudes_muestra"
    )
    paso_actual = models.PositiveSmallIntegerField("paso actual", default=1)
    cantidad_botes_basura = models.PositiveIntegerField("cantidad de botes de basura", default=0)
    cantidad_extintores = models.PositiveIntegerField("cantidad de extintores", default=0)
    modelo_botes_basura = models.CharField("modelo o nombre del bote de basura", max_length=150, blank=True)
    modelo_extintores = models.CharField("modelo o nombre del extintor", max_length=150, blank=True)
    foto_botes_basura = models.FileField(
        "foto de los botes de basura", upload_to=_ruta_foto_equipamiento, blank=True
    )
    foto_extintores = models.FileField(
        "foto de los extintores", upload_to=_ruta_foto_equipamiento, blank=True
    )
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    fecha_actualizacion = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"

    def __str__(self) -> str:
        return self.nombre_comercio or f"Solicitud {self.pk}"

    @property
    def paso1_completo(self) -> bool:
        return bool(
            self.nombre_comercio
            and self.giro
            and self.subgiro
            and self.programa_especial
            and (self.programa_especial == "NINGUNO" or self.folio_programa_social)
            and self.producto_principal_id
            and self.productos.exists()
        )

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


class ProductoSolicitud(models.Model):
    solicitud = models.ForeignKey(
        SolicitudMuestra, on_delete=models.CASCADE, related_name="detalle_productos"
    )
    producto = models.ForeignKey("expediente.Producto", on_delete=models.PROTECT)
    stock_total = models.PositiveIntegerField("cantidad de stock total")
    precio_venta = models.DecimalField("precio de venta", max_digits=12, decimal_places=2)
    factura = models.FileField("factura para el evento", upload_to="muestras/facturas/productos/", blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["solicitud", "producto"], name="producto_unico_por_solicitud")]


class MobiliarioSolicitud(models.Model):
    solicitud = models.ForeignKey(
        SolicitudMuestra, on_delete=models.CASCADE, related_name="detalle_mobiliario"
    )
    mobiliario = models.ForeignKey("expediente.Mobiliario", on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField("cantidad")
    factura = models.FileField("factura para el evento", upload_to="muestras/facturas/mobiliario/", blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["solicitud", "mobiliario"], name="mobiliario_unico_por_solicitud")]
