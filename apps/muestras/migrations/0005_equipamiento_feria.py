from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("muestras", "0004_detalle_participacion")]
    operations = [
        migrations.AddField(
            model_name="solicitudmuestra",
            name="cantidad_botes_basura",
            field=models.PositiveIntegerField(default=0, verbose_name="cantidad de botes de basura"),
        ),
        migrations.AddField(
            model_name="solicitudmuestra",
            name="cantidad_extintores",
            field=models.PositiveIntegerField(default=0, verbose_name="cantidad de extintores"),
        ),
    ]
