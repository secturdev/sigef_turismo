from django.db import migrations, models


def configure_required_documents(apps, schema_editor):
    TipoDocumento = apps.get_model("expediente", "TipoDocumento")
    fisica = "PERSONA_FISICA"
    moral = "PERSONA_MORAL"
    documents = (
        ("INE", "INE", 10, ["CIUDADANO", fisica], True, None),
        ("CURP", "CURP", 15, [fisica], True, None),
        ("COMPROBANTE_DOMICILIO", "Comprobante de domicilio", 20, ["CIUDADANO", fisica], True, 90),
        ("CONSTANCIA_SITUACION_FISCAL", "Constancia de situación fiscal", 30, [fisica], False, 30),
        ("INE_REPRESENTANTE", "INE del representante", 10, [moral], True, None),
        ("CURP_REPRESENTANTE_LEGAL", "CURP del representante legal", 15, [moral], True, None),
        ("COMPROBANTE_DOMICILIO_EMPRESA", "Comprobante de domicilio de la empresa", 20, [moral], True, 90),
        ("ACTA_CONSTITUTIVA", "Acta constitutiva de la empresa", 30, [moral], True, None),
        ("PODER_NOTARIAL", "Poder notarial de la empresa", 40, [moral], True, None),
        ("CONSTANCIA_SITUACION_FISCAL_EMPRESA", "Constancia de situación fiscal de la empresa", 50, [moral], True, 30),
    )
    for clave, nombre, orden, tipos, obligatorio, vigencia in documents:
        TipoDocumento.objects.update_or_create(
            clave=clave,
            defaults={
                "nombre": nombre,
                "orden": orden,
                "tipos_persona": tipos,
                "obligatorio": obligatorio,
                "dias_vigencia": vigencia,
                "activo": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("expediente", "0002_ensure_new_columns")]

    operations = [
        migrations.AddField(
            model_name="tipodocumento",
            name="obligatorio",
            field=models.BooleanField(default=True, verbose_name="obligatorio"),
        ),
        migrations.RunPython(configure_required_documents, migrations.RunPython.noop),
    ]
