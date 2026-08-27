from __future__ import annotations

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.autenticacion.models import Usuario
from apps.expediente.models import (
    CampoAdicional,
    Documento,
    Expediente,
    TipoDocumento,
    ValorCampoAdicional,
    VersionDocumento,
)
from apps.expediente.forms import GeneralDataForm
from apps.expediente.services import (
    ESTADO_VENCIDO,
    ESTADO_VIGENTE,
    calculate_document_status,
    calculate_expediente_progress,
    get_or_create_expediente,
    save_additional_fields,
    set_tipo_persona,
    update_datos_generales,
    upload_document_version,
)
from apps.expediente.validators import validate_curp, validate_rfc


class ExpedienteRulesTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            correo="uno@example.com",
            password="ClaveSegura123!",
        )
        self.expediente = get_or_create_expediente(self.user)

    def test_one_expediente_per_user(self):
        second = get_or_create_expediente(self.user)
        self.assertEqual(self.expediente.pk, second.pk)
        self.assertEqual(Expediente.objects.filter(usuario=self.user).count(), 1)

    def test_persona_fisica_requires_curp(self):
        set_tipo_persona(self.expediente, Expediente.TipoPersona.PERSONA_FISICA)
        with self.assertRaises(ValidationError):
            update_datos_generales(
                self.expediente,
                {
                    "nombres": "Juan",
                    "apellido_paterno": "Pérez",
                    "apellido_materno": "López",
                    "curp": "",
                    "telefono": "9931234567",
                    "correo_contacto": "juan@example.com",
                },
            )
        update_datos_generales(
            self.expediente,
            {
                "nombres": "Juan",
                "apellido_paterno": "Pérez",
                "apellido_materno": "López",
                "curp": "PELJ800101HDFRRN09",
                "telefono": "9931234567",
                "correo_contacto": "juan@example.com",
            },
        )
        self.assertEqual(self.expediente.datos_generales.curp, "PELJ800101HDFRRN09")

    def test_ciudadano_requires_curp_celular_correo(self):
        set_tipo_persona(self.expediente, Expediente.TipoPersona.CIUDADANO)
        with self.assertRaises(ValidationError):
            update_datos_generales(
                self.expediente,
                {
                    "nombres": "Ana",
                    "apellido_paterno": "Ruiz",
                    "apellido_materno": "Díaz",
                    "curp": "PELJ800101HDFRRN09",
                    "telefono": "9931234567",
                    "correo_contacto": "",
                },
            )
        update_datos_generales(
            self.expediente,
            {
                "nombres": "Ana",
                "apellido_paterno": "Ruiz",
                "apellido_materno": "Díaz",
                "curp": "PELJ800101HDFRRN09",
                "telefono": "9931234567",
                "correo_contacto": "ana@example.com",
            },
        )
        self.assertEqual(self.expediente.datos_generales.correo_contacto, "ana@example.com")

    def test_persona_moral_requires_curp_representante(self):
        set_tipo_persona(self.expediente, Expediente.TipoPersona.PERSONA_MORAL)
        with self.assertRaises(ValidationError):
            update_datos_generales(
                self.expediente,
                {
                    "nombres": "Empresa",
                    "curp": "",
                    "representante_legal": "Ana López",
                },
            )
        update_datos_generales(
            self.expediente,
            {
                "nombres": "Empresa Demo",
                "curp": "PELJ800101HDFRRN09",
                "representante_legal": "Ana López",
            },
        )
        self.assertEqual(self.expediente.datos_generales.curp, "PELJ800101HDFRRN09")
        self.assertEqual(
            self.expediente.datos_generales.representante_legal, "Ana López"
        )

    def test_curp_and_rfc_validators(self):
        self.assertEqual(validate_curp("pelj800101hdfrrn09"), "PELJ800101HDFRRN09")
        with self.assertRaises(ValidationError):
            validate_curp("INVALIDO")
        self.assertEqual(validate_rfc("ede800101abc"), "EDE800101ABC")
        with self.assertRaises(ValidationError):
            validate_rfc("XX")

    def test_oidc_identity_fields_ignore_posted_changes(self):
        form = GeneralDataForm(
            data={
                "nombres": "NOMBRE ALTERADO",
                "apellido_paterno": "APELLIDO ALTERADO",
                "apellido_materno": "OTRO",
                "curp": "PELJ800101HDFRRN09",
                "telefono": "9931234567",
                "correo_contacto": "alterado@example.com",
            },
            initial={
                "nombres": "SANTIAGO",
                "apellido_paterno": "REAL",
                "apellido_materno": "CALCANEO",
                "correo_contacto": "original@example.com",
            },
            tipo_persona=Expediente.TipoPersona.CIUDADANO,
            identidad_oidc=True,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["nombres"], "SANTIAGO")
        self.assertEqual(form.cleaned_data["apellido_paterno"], "REAL")
        self.assertEqual(form.cleaned_data["apellido_materno"], "CALCANEO")
        self.assertEqual(form.cleaned_data["correo_contacto"], "original@example.com")


class AdditionalFieldsTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            correo="extra@example.com",
            password="ClaveSegura123!",
        )
        self.expediente = get_or_create_expediente(self.user)
        set_tipo_persona(self.expediente, Expediente.TipoPersona.CIUDADANO)
        self.campo = CampoAdicional.objects.create(
            clave="ocupacion",
            etiqueta="Ocupación",
            tipo_dato=CampoAdicional.TipoDato.TEXTO,
            obligatorio=True,
            activo=True,
            orden=1,
            tipos_persona=[Expediente.TipoPersona.CIUDADANO],
        )

    def test_save_additional_field(self):
        save_additional_fields(self.expediente, {"ocupacion": "Comerciante"})
        valor = ValorCampoAdicional.objects.get(
            expediente=self.expediente, campo=self.campo
        )
        self.assertEqual(valor.valor, "Comerciante")


class DocumentTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            correo="docs@example.com",
            password="ClaveSegura123!",
        )
        self.other = Usuario.objects.create_user(
            correo="otro@example.com",
            password="ClaveSegura123!",
        )
        self.expediente = get_or_create_expediente(self.user)
        self.tipo, _ = TipoDocumento.objects.get_or_create(
            clave="INE",
            defaults={
                "nombre": "INE",
                "activo": True,
                "tipos_persona": [Expediente.TipoPersona.CIUDADANO],
            },
        )

    def _pdf(self, name="ine.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4 test", content_type="application/pdf"
        )

    def test_upload_creates_version_and_keeps_previous(self):
        v1 = upload_document_version(
            self.expediente, self.tipo, self._pdf("v1.pdf"), usuario=self.user
        )
        v2 = upload_document_version(
            self.expediente, self.tipo, self._pdf("v2.pdf"), usuario=self.user
        )
        doc = Documento.objects.get(expediente=self.expediente, tipo_documento=self.tipo)
        self.assertEqual(doc.version_actual_id, v2.pk)
        self.assertEqual(doc.versiones.count(), 2)
        self.assertTrue(VersionDocumento.objects.filter(pk=v1.pk).exists())
        self.assertTrue(v1.archivo.storage.exists(v1.archivo.name))

    def test_expired_document_detected(self):
        version = upload_document_version(
            self.expediente,
            self.tipo,
            self._pdf(),
            fecha_vencimiento=date.today() - timedelta(days=1),
            usuario=self.user,
        )
        self.assertEqual(calculate_document_status(version), ESTADO_VENCIDO)
        version.fecha_vencimiento = date.today() + timedelta(days=60)
        version.save(update_fields=["fecha_vencimiento"])
        self.assertEqual(calculate_document_status(version), ESTADO_VIGENTE)

    def test_other_user_cannot_download(self):
        version = upload_document_version(
            self.expediente, self.tipo, self._pdf(), usuario=self.user
        )
        client = Client()
        client.force_login(self.other)
        response = client.get(
            reverse("expediente:download_version", kwargs={"version_id": version.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_can_download(self):
        version = upload_document_version(
            self.expediente, self.tipo, self._pdf(), usuario=self.user
        )
        client = Client()
        client.force_login(self.user)
        response = client.get(
            reverse("expediente:download_version", kwargs={"version_id": version.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_progress_increases(self):
        progress = calculate_expediente_progress(self.expediente)
        self.assertEqual(progress["percent"], 0)
        set_tipo_persona(self.expediente, Expediente.TipoPersona.CIUDADANO)
        update_datos_generales(
            self.expediente,
            {
                "nombres": "Ana",
                "apellido_paterno": "Ruiz",
                "apellido_materno": "Díaz",
                "curp": "PELJ800101HDFRRN09",
                "telefono": "9931234567",
                "correo_contacto": "ana@example.com",
            },
        )
        progress = calculate_expediente_progress(self.expediente)
        self.assertGreater(progress["percent"], 0)
