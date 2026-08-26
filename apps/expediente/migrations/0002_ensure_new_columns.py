from django.db import migrations


def _add_column(schema_editor, table, column, sql_type, default_sql=None):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            [table, column],
        )
        if cursor.fetchone():
            return
        default_clause = f" DEFAULT {default_sql}" if default_sql is not None else ""
        cursor.execute(
            f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}{default_clause}'
        )


def forwards(apps, schema_editor):
    # Idempotente: en BD nueva 0001 ya creó las columnas; en BD vieja las agrega.
    _add_column(schema_editor, "expediente_datosgenerales", "telefono", "varchar(20)", "''")
    _add_column(
        schema_editor, "expediente_datosgenerales", "correo_contacto", "varchar(254)", "''"
    )
    _add_column(
        schema_editor, "expediente_datosgenerales", "domicilio", "varchar(255)", "''"
    )
    _add_column(
        schema_editor,
        "expediente_datosgenerales",
        "representante_legal",
        "varchar(200)",
        "''",
    )
    _add_column(schema_editor, "expediente_tipodocumento", "orden", "integer", "0")
    _add_column(
        schema_editor,
        "expediente_tipodocumento",
        "tipos_persona",
        "jsonb",
        "'[]'::jsonb",
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("expediente", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
