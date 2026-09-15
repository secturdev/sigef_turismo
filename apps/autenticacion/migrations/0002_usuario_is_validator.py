from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("autenticacion", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="is_validator",
            field=models.BooleanField(default=False, verbose_name="es validador"),
        ),
    ]
