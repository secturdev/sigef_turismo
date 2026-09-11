from django.core.validators import FileExtensionValidator
from django.db import models


class Evento(models.Model):
    boletab_eventos = models.JSONField("eventos de Boletab", default=list, blank=True)
    catalogo_giros = models.JSONField(default=list, blank=True)
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


class ReglaEspacio(models.Model):
    evento = models.ForeignKey(
        Evento, on_delete=models.CASCADE, related_name="reglas_espacios"
    )
    boletab_evento_id = models.CharField(max_length=100)
    asiento_id = models.CharField(max_length=100)
    etiqueta = models.CharField(max_length=250, blank=True)
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
