from django.db import migrations, models
import django.db.models.deletion
import apps.muestras.constants


class Migration(migrations.Migration):
    dependencies = [("expediente", "0007_mobiliario_tipo"), ("muestras", "0006_fotos_equipamiento")]
    operations = [
        migrations.AlterModelOptions(name="solicitudmuestra", options={"verbose_name": "solicitud", "verbose_name_plural": "solicitudes"}),
        migrations.AddField(model_name="solicitudmuestra", name="subgiro", field=models.CharField(blank=True, choices=apps.muestras.constants.SUBGIROS, max_length=64, verbose_name="subgiro")),
        migrations.AddField(model_name="solicitudmuestra", name="folio_programa_social", field=models.CharField(blank=True, max_length=100, verbose_name="folio del programa social")),
        migrations.AddField(model_name="solicitudmuestra", name="modelo_botes_basura", field=models.CharField(blank=True, max_length=150, verbose_name="modelo o nombre del bote de basura")),
        migrations.AddField(model_name="solicitudmuestra", name="modelo_extintores", field=models.CharField(blank=True, max_length=150, verbose_name="modelo o nombre del extintor")),
        migrations.AddField(model_name="solicitudmuestra", name="producto_principal", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="solicitudes_como_principal", to="expediente.producto", verbose_name="producto principal")),
        migrations.AlterField(model_name="solicitudmuestra", name="programa_especial", field=models.CharField(blank=True, choices=[("NINGUNO", "No pertenezco a un programa social"), ("ORIGEN_TABASCO", "Origen Tabasco"), ("TANDAS_MUJER", "Tandas para la Mujer"), ("CODIGO_BARRAS", "Código de Barras")], max_length=64, verbose_name="programa especial")),
    ]
