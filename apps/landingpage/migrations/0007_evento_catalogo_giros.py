from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("landingpage", "0006_evento_giros_subgiros_disponibles")]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="catalogo_giros",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
