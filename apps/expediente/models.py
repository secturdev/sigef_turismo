from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

from .storage import PrivateMediaStorage


def private_document_storage():
    return PrivateMediaStorage()


class Expediente(models.Model):
    class TipoPersona(models.TextChoices):
        PERSONA_FISICA = "PERSONA_FISICA", "Persona física"
        PERSONA_MORAL = "PERSONA_MORAL", "Persona moral"
        CIUDADANO = "CIUDADANO", "Ciudadano"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expediente",
        verbose_name="usuario",
    )
    tipo_persona = models.CharField(
        "tipo de persona",
        max_length=32,
        choices=TipoPersona.choices,
        blank=True,
    )
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    fecha_actualizacion = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        verbose_name = "expediente"
        verbose_name_plural = "expedientes"

    def __str__(self) -> str:
        return f"Expediente #{self.pk} — {self.usuario}"


class DatosGenerales(models.Model):
    expediente = models.OneToOneField(
        Expediente,
        on_delete=models.CASCADE,
        related_name="datos_generales",
        verbose_name="expediente",
    )
    nombres = models.CharField(
        "nombres / razón social",
        max_length=150,
        blank=True,
        help_text="Nombre(s) o razón social según el tipo de persona.",
    )
    apellido_paterno = models.CharField("apellido paterno", max_length=100, blank=True)
    apellido_materno = models.CharField("apellido materno", max_length=100, blank=True)
    curp = models.CharField("CURP", max_length=18, blank=True)
    rfc = models.CharField("RFC", max_length=13, blank=True)
    telefono = models.CharField("número de celular", max_length=20, blank=True)
    correo_contacto = models.EmailField("correo electrónico", blank=True)
    domicilio = models.CharField("domicilio", max_length=255, blank=True)
    representante_legal = models.CharField(
        "representante legal",
        max_length=200,
        blank=True,
    )
    fecha_actualizacion = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        verbose_name = "datos generales"
        verbose_name_plural = "datos generales"

    def __str__(self) -> str:
        return f"Datos de expediente #{self.expediente_id}"


class CampoAdicional(models.Model):
    class TipoDato(models.TextChoices):
        TEXTO = "TEXTO", "Texto"
        NUMERO = "NUMERO", "Número"
        FECHA = "FECHA", "Fecha"
        BOOLEANO = "BOOLEANO", "Sí/No"

    clave = models.SlugField("clave", max_length=64, unique=True)
    etiqueta = models.CharField("etiqueta", max_length=150)
    tipo_dato = models.CharField(
        "tipo de dato",
        max_length=16,
        choices=TipoDato.choices,
        default=TipoDato.TEXTO,
    )
    obligatorio = models.BooleanField("obligatorio", default=False)
    activo = models.BooleanField("activo", default=True)
    orden = models.PositiveIntegerField("orden", default=0)
    # Lista de tipos de persona aplicables, ej. ["PERSONA_FISICA", "CIUDADANO"].
    tipos_persona = models.JSONField("tipos de persona", default=list, blank=True)

    class Meta:
        ordering = ["orden", "clave"]
        verbose_name = "campo adicional"
        verbose_name_plural = "campos adicionales"

    def __str__(self) -> str:
        return self.etiqueta


class ValorCampoAdicional(models.Model):
    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="valores_adicionales",
        verbose_name="expediente",
    )
    campo = models.ForeignKey(
        CampoAdicional,
        on_delete=models.PROTECT,
        related_name="valores",
        verbose_name="campo",
    )
    valor = models.JSONField("valor", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expediente", "campo"],
                name="uniq_valor_campo_por_expediente",
            )
        ]
        verbose_name = "valor de campo adicional"
        verbose_name_plural = "valores de campos adicionales"

    def __str__(self) -> str:
        return f"{self.campo.clave} @ expediente {self.expediente_id}"


class TipoDocumento(models.Model):
    clave = models.SlugField("clave", max_length=64, unique=True)
    nombre = models.CharField("nombre", max_length=150)
    activo = models.BooleanField("activo", default=True)
    orden = models.PositiveIntegerField("orden", default=0)
    dias_vigencia = models.PositiveIntegerField(
        "días de vigencia",
        null=True,
        blank=True,
        help_text="Si hay emisión y no hay vencimiento, se calcula con este valor.",
    )

    tipos_persona = models.JSONField("tipos de persona", default=list, blank=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "tipo de documento"
        verbose_name_plural = "tipos de documento"

    def __str__(self) -> str:
        return self.nombre

    def aplica_a(self, tipo_persona: str) -> bool:
        if not self.tipos_persona:
            return True
        return tipo_persona in self.tipos_persona


def _ruta_version_documento(instance: VersionDocumento, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return (
        f"private/documentos/"
        f"{instance.documento.expediente_id}/"
        f"{instance.documento_id}/"
        f"{safe_name}"
    )


class Documento(models.Model):
    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="expediente",
    )
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        related_name="documentos",
        verbose_name="tipo de documento",
    )
    version_actual = models.ForeignKey(
        "VersionDocumento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="versión actual",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expediente", "tipo_documento"],
                name="uniq_documento_tipo_por_expediente",
            )
        ]
        verbose_name = "documento"
        verbose_name_plural = "documentos"

    def __str__(self) -> str:
        return f"{self.tipo_documento} — expediente {self.expediente_id}"


class VersionDocumento(models.Model):
    documento = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name="versiones",
        verbose_name="documento",
    )
    archivo = models.FileField(
        "archivo",
        upload_to=_ruta_version_documento,
        storage=private_document_storage,
    )
    nombre_original = models.CharField("nombre original", max_length=255)
    fecha_carga = models.DateTimeField("fecha de carga", auto_now_add=True)
    fecha_emision = models.DateField("fecha de emisión", null=True, blank=True)
    fecha_vencimiento = models.DateField("fecha de vencimiento", null=True, blank=True)
    hash_sha256 = models.CharField("hash SHA-256", max_length=64, blank=True)

    class Meta:
        ordering = ["-fecha_carga"]
        verbose_name = "versión de documento"
        verbose_name_plural = "versiones de documento"

    def __str__(self) -> str:
        return f"v{self.pk} — {self.nombre_original}"
