from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("landingpage", "0008_evento_catalogo_folios")]

    operations = [
        migrations.CreateModel(
            name="ReglaSeccion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("boletab_evento_id", models.CharField(max_length=100)),
                ("seccion_id", models.CharField(max_length=100)),
                ("seccion_nombre", models.CharField(blank=True, max_length=250)),
                ("reglas", models.JSONField(blank=True, default=list)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("evento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reglas_secciones", to="landingpage.evento")),
            ],
            options={"verbose_name": "regla de sección", "verbose_name_plural": "reglas de secciones"},
        ),
        migrations.AddConstraint(
            model_name="reglaseccion",
            constraint=models.UniqueConstraint(fields=("evento", "boletab_evento_id", "seccion_id"), name="regla_unica_por_seccion_boletab"),
        ),
    ]
