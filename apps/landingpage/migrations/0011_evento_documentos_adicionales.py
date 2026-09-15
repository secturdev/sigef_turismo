from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("landingpage", "0010_reglaespacio_estado_plantilla")]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="documentos_adicionales",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
