from django.core.validators import FileExtensionValidator
from django.db import models


class Evento(models.Model):
    boletab_eventos = models.JSONField("eventos de Boletab", default=list, blank=True)
    catalogo_giros = models.JSONField(default=list, blank=True)
    catalogo_folios = models.JSONField(default=list, blank=True)
    documentos_adicionales = models.JSONField(default=list, blank=True)
    equipamiento_obligatorio = models.JSONField("equipamiento obligatorio", default=list, blank=True)
    giros_disponibles = models.JSONField(default=list, blank=True)
    subgiros_disponibles = models.JSONField(default=list, blank=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField()
    imagen = models.FileField(
        upload_to="eventos/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    visible = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha_registro",)
        verbose_name = "evento"
        verbose_name_plural = "eventos"

    def __str__(self):
        return self.nombre

    def documentos_requeridos(self, tipo_persona):
        """Combine the global profile catalog with this event's extra requirements."""
        from apps.expediente.models import TipoDocumento

        inherited = [
            {
                "id": f"global-{document.pk}",
                "origen": "GLOBAL",
                "tipo_documento_id": document.pk,
                "nombre": document.nombre,
                "tipos_persona": document.tipos_persona,
                "obligatorio": document.obligatorio,
                "max_mb": 10,
            }
            for document in TipoDocumento.objects.filter(activo=True)
            if document.aplica_a(tipo_persona)
        ]
        extras = [
            requirement
            for requirement in self.documentos_adicionales
            if tipo_persona in requirement.get("tipos_persona", [])
        ]
        return inherited + extras


class ReglaEspacio(models.Model):
    class EstadoPlantilla(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        AUSENTE = "AUSENTE", "Ya no existe en Boletab"
        MODIFICADO = "MODIFICADO", "Fue modificado en Boletab"

    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name="reglas_espacios"
    )
    boletab_evento_id = models.CharField(max_length=100)
    asiento_id = models.CharField(max_length=100)
    etiqueta = models.CharField(max_length=250, blank=True)
    boletab_seccion_id = models.CharField(max_length=100, blank=True)
    estado_plantilla = models.CharField(
        max_length=20, choices=EstadoPlantilla.choices, default=EstadoPlantilla.VIGENTE
    )
    ultima_validacion = models.DateTimeField(null=True, blank=True)
    reglas = models.JSONField(default=list, blank=True)
    giros = models.JSONField(default=list, blank=True)
    subgiros = models.JSONField(default=list, blank=True)
    folios = models.JSONField(default=list, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("evento", "boletab_evento_id", "asiento_id"),
                name="regla_unica_por_espacio_boletab",
            )
        ]
        verbose_name = "regla de espacio"
        verbose_name_plural = "reglas de espacios"


class ReglaSeccion(models.Model):
    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name="reglas_secciones"
    )
    boletab_evento_id = models.CharField(max_length=100)
    seccion_id = models.CharField(max_length=100)
    seccion_nombre = models.CharField(max_length=250, blank=True)
    reglas = models.JSONField(default=list, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("evento", "boletab_evento_id", "seccion_id"),
                name="regla_unica_por_seccion_boletab",
            )
        ]
        verbose_name = "regla de sección"
        verbose_name_plural = "reglas de secciones"
