from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("landingpage", "0005_reglaespacio_reglas"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="giros_disponibles",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="evento",
            name="subgiros_disponibles",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
