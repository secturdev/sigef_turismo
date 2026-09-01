from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("expediente", "0006_comercio"),
        ("muestras", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudmuestra",
            name="productos",
            field=models.ManyToManyField(blank=True, related_name="solicitudes_muestra", to="expediente.producto"),
        ),
        migrations.AddField(
            model_name="solicitudmuestra",
            name="mobiliario",
            field=models.ManyToManyField(blank=True, related_name="solicitudes_muestra", to="expediente.mobiliario"),
        ),
    ]
