from django.db import migrations, models
import django.db.models.deletion
import apps.expediente.models


class Migration(migrations.Migration):
    dependencies = [("expediente", "0004_producto")]

    operations = [
        migrations.CreateModel(
            name="Mobiliario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150, verbose_name="nombre")),
                ("descripcion", models.TextField(max_length=1000, verbose_name="descripción")),
                ("imagen", models.FileField(storage=apps.expediente.models.private_document_storage, upload_to=apps.expediente.models._ruta_imagen_mobiliario, verbose_name="imagen")),
                ("factura", models.FileField(blank=True, storage=apps.expediente.models.private_document_storage, upload_to=apps.expediente.models._ruta_factura_mobiliario, verbose_name="factura")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("expediente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobiliario", to="expediente.expediente")),
            ],
            options={"verbose_name": "mobiliario", "verbose_name_plural": "mobiliario", "ordering": ["nombre"]},
        )
    ]
