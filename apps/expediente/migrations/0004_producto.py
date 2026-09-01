from django.db import migrations, models
import django.db.models.deletion
import apps.expediente.models


class Migration(migrations.Migration):
    dependencies = [("expediente", "0003_tipodocumento_obligatorio")]

    operations = [
        migrations.CreateModel(
            name="Producto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150, verbose_name="nombre del producto")),
                ("imagen", models.FileField(storage=apps.expediente.models.private_document_storage, upload_to=apps.expediente.models._ruta_imagen_producto, verbose_name="imagen del producto")),
                ("factura", models.FileField(blank=True, storage=apps.expediente.models.private_document_storage, upload_to=apps.expediente.models._ruta_factura_producto, verbose_name="factura")),
                ("descripcion", models.TextField(max_length=1000, verbose_name="descripción del producto")),
                ("es_principal", models.BooleanField(default=False, verbose_name="producto principal")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True, verbose_name="fecha de creación")),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True, verbose_name="fecha de actualización")),
                ("expediente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="productos", to="expediente.expediente", verbose_name="expediente")),
            ],
            options={"verbose_name": "producto", "verbose_name_plural": "productos", "ordering": ["-es_principal", "nombre"]},
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(condition=models.Q(("es_principal", True)), fields=("expediente",), name="un_producto_principal_por_expediente"),
        ),
    ]
