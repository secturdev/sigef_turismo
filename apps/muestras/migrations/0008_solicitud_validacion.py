from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("muestras", "0007_detalle_comercial_equipamiento"),
    ]

    operations = [
        migrations.AddField(model_name="solicitudmuestra", name="estado", field=models.CharField(choices=[("BORRADOR", "Borrador"), ("EN_REVISION", "En revisión"), ("APROBADA", "Aprobada"), ("RECHAZADA", "Rechazada")], default="BORRADOR", max_length=20, verbose_name="estado")),
        migrations.AddField(model_name="solicitudmuestra", name="observaciones_validacion", field=models.TextField(blank=True, verbose_name="observaciones de validación")),
        migrations.AddField(model_name="solicitudmuestra", name="fecha_envio", field=models.DateTimeField(blank=True, null=True, verbose_name="fecha de envío")),
        migrations.AddField(model_name="solicitudmuestra", name="fecha_validacion", field=models.DateTimeField(blank=True, null=True, verbose_name="fecha de validación")),
        migrations.AddField(model_name="solicitudmuestra", name="validada_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="solicitudes_validadas", to=settings.AUTH_USER_MODEL, verbose_name="validada por")),
    ]
