from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expediente", "0006_comercio")]
    operations = [
        migrations.AddField(
            model_name="mobiliario",
            name="tipo",
            field=models.CharField(choices=[("GENERAL", "General"), ("BOTE_BASURA", "Bote de basura"), ("EXTINTOR", "Extintor")], default="GENERAL", max_length=24, verbose_name="tipo"),
        )
    ]
