from django.db import migrations, models

import apps.muestras.models


class Migration(migrations.Migration):
    dependencies = [("muestras", "0005_equipamiento_feria")]

    operations = [
        migrations.AddField(
            model_name="solicitudmuestra",
            name="foto_botes_basura",
            field=models.FileField(blank=True, upload_to=apps.muestras.models._ruta_foto_equipamiento, verbose_name="foto de los botes de basura"),
        ),
        migrations.AddField(
            model_name="solicitudmuestra",
            name="foto_extintores",
            field=models.FileField(blank=True, upload_to=apps.muestras.models._ruta_foto_equipamiento, verbose_name="foto de los extintores"),
        ),
    ]
