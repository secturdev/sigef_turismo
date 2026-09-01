from django.db import migrations, models
import django.db.models.deletion
import apps.expediente.models


class Migration(migrations.Migration):
    dependencies = [("expediente", "0005_mobiliario")]

    operations = [
        migrations.CreateModel(
            name="Comercio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=200, verbose_name="nombre de mi comercio")),
                ("logo", models.FileField(storage=apps.expediente.models.private_document_storage, upload_to=apps.expediente.models._ruta_logo_comercio, verbose_name="logo de mi comercio")),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("expediente", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="comercio", to="expediente.expediente")),
            ],
            options={"verbose_name": "comercio", "verbose_name_plural": "comercios"},
        )
    ]
