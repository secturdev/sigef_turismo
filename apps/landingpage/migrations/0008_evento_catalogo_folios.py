from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("landingpage", "0007_evento_catalogo_giros")]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="catalogo_folios",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
