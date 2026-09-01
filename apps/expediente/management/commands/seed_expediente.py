from django.core.management.base import BaseCommand

from apps.expediente.models import CampoAdicional, Expediente, TipoDocumento

FISICA = Expediente.TipoPersona.PERSONA_FISICA
MORAL = Expediente.TipoPersona.PERSONA_MORAL
CIUDADANO = Expediente.TipoPersona.CIUDADANO

TIPOS_DOCUMENTO = [
    {
        "clave": "INE",
        "nombre": "INE",
        "dias_vigencia": None,
        "orden": 10,
        "tipos_persona": [CIUDADANO, FISICA],
        "obligatorio": True,
    },
    {
        "clave": "CURP",
        "nombre": "CURP",
        "dias_vigencia": None,
        "orden": 15,
        "tipos_persona": [FISICA],
        "obligatorio": True,
    },
    {
        "clave": "COMPROBANTE_DOMICILIO",
        "nombre": "Comprobante de domicilio",
        "dias_vigencia": 90,
        "orden": 20,
        "tipos_persona": [CIUDADANO, FISICA],
        "obligatorio": True,
    },
    {
        "clave": "CONSTANCIA_SITUACION_FISCAL",
        "nombre": "Constancia de situación fiscal",
        "dias_vigencia": 30,
        "orden": 30,
        "tipos_persona": [FISICA],
        "obligatorio": False,
    },
    {
        "clave": "INE_REPRESENTANTE",
        "nombre": "INE del representante",
        "dias_vigencia": None,
        "orden": 10,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
    {
        "clave": "CURP_REPRESENTANTE_LEGAL",
        "nombre": "CURP del representante legal",
        "dias_vigencia": None,
        "orden": 15,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
    {
        "clave": "COMPROBANTE_DOMICILIO_EMPRESA",
        "nombre": "Comprobante de domicilio de la empresa",
        "dias_vigencia": 90,
        "orden": 20,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
    {
        "clave": "ACTA_CONSTITUTIVA",
        "nombre": "Acta constitutiva de la empresa",
        "dias_vigencia": None,
        "orden": 30,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
    {
        "clave": "PODER_NOTARIAL",
        "nombre": "Poder notarial de la empresa",
        "dias_vigencia": None,
        "orden": 40,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
    {
        "clave": "CONSTANCIA_SITUACION_FISCAL_EMPRESA",
        "nombre": "Constancia de situación fiscal de la empresa",
        "dias_vigencia": 30,
        "orden": 50,
        "tipos_persona": [MORAL],
        "obligatorio": True,
    },
]

CLAVES_DOCUMENTO_ACTIVAS = {item["clave"] for item in TIPOS_DOCUMENTO}


class Command(BaseCommand):
    help = "Carga el catálogo definitivo de documentos del expediente global."

    def handle(self, *args, **options):
        docs_created = 0
        for item in TIPOS_DOCUMENTO:
            _, was_created = TipoDocumento.objects.update_or_create(
                clave=item["clave"],
                defaults={
                    "nombre": item["nombre"],
                    "activo": True,
                    "dias_vigencia": item["dias_vigencia"],
                    "orden": item["orden"],
                    "tipos_persona": item["tipos_persona"],
                    "obligatorio": item["obligatorio"],
                },
            )
            if was_created:
                docs_created += 1

        docs_deactivated = TipoDocumento.objects.exclude(
            clave__in=CLAVES_DOCUMENTO_ACTIVAS
        ).filter(activo=True).update(activo=False)

        campos_deactivated = CampoAdicional.objects.filter(activo=True).update(
            activo=False
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Documentos activos: {len(TIPOS_DOCUMENTO)} "
                f"(nuevos: {docs_created}, desactivados: {docs_deactivated}). "
                f"Campos adicionales desactivados: {campos_deactivated}."
            )
        )
