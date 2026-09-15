from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("landingpage", "0009_reglaseccion")]

    operations = [
        migrations.AddField(
            model_name="reglaespacio",
            name="boletab_seccion_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="reglaespacio",
            name="estado_plantilla",
            field=models.CharField(
                choices=[
                    ("VIGENTE", "Vigente"),
                    ("AUSENTE", "Ya no existe en Boletab"),
                    ("MODIFICADO", "Fue modificado en Boletab"),
                ],
                default="VIGENTE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reglaespacio",
            name="ultima_validacion",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
