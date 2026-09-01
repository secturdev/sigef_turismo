from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("expediente", "0007_mobiliario_tipo"), ("muestras", "0003_solicitud_catalogos")]
    operations = [
        migrations.CreateModel(
            name="ProductoSolicitud",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stock_total", models.PositiveIntegerField(verbose_name="cantidad de stock total")),
                ("precio_venta", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="precio de venta")),
                ("factura", models.FileField(blank=True, upload_to="muestras/facturas/productos/", verbose_name="factura para el evento")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="expediente.producto")),
                ("solicitud", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalle_productos", to="muestras.solicitudmuestra")),
            ],
        ),
        migrations.CreateModel(
            name="MobiliarioSolicitud",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.PositiveIntegerField(verbose_name="cantidad")),
                ("factura", models.FileField(blank=True, upload_to="muestras/facturas/mobiliario/", verbose_name="factura para el evento")),
                ("mobiliario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="expediente.mobiliario")),
                ("solicitud", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalle_mobiliario", to="muestras.solicitudmuestra")),
            ],
        ),
        migrations.AddConstraint(model_name="productosolicitud", constraint=models.UniqueConstraint(fields=("solicitud", "producto"), name="producto_unico_por_solicitud")),
        migrations.AddConstraint(model_name="mobiliariosolicitud", constraint=models.UniqueConstraint(fields=("solicitud", "mobiliario"), name="mobiliario_unico_por_solicitud")),
    ]
