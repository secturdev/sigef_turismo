import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from apps.autenticacion.models import Usuario
from apps.autenticacion.oidc import LlaveTabascoOIDCBackend, _log_oidc_claims
from apps.expediente.models import DatosGenerales
from apps.landingpage.models import Evento, ReglaEspacio

import tempfile
from unittest.mock import patch


class AuthTests(TestCase):
    def test_admin_can_login_with_email_and_password(self):
        Usuario.objects.create_superuser(
            correo="admin@example.com", password="Temporal01"
        )

        response = self.client.post(
            reverse("autenticacion:admin_login"),
            {"correo": "admin@example.com", "password": "Temporal01"},
        )

        self.assertRedirects(response, reverse("autenticacion:admin_dashboard"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            Usuario.objects.get(correo="admin@example.com").pk,
        )

    def test_regular_user_cannot_login_through_admin_access(self):
        Usuario.objects.create_user(
            correo="user@example.com", password="Temporal01"
        )

        response = self.client.post(
            reverse("autenticacion:admin_login"),
            {"correo": "user@example.com", "password": "Temporal01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no tiene acceso al panel")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_can_create_another_admin(self):
        admin = Usuario.objects.create_superuser(
            correo="owner@example.com", password="TemporaryOwner01"
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("autenticacion:admin_users"),
            {
                "nombre_visible": "Nueva Administradora",
                "correo": "new-admin@example.com",
                "password": "SafeTemporary2026!",
                "password_confirmation": "SafeTemporary2026!",
            },
        )

        self.assertRedirects(response, reverse("autenticacion:admin_users"))
        created = Usuario.objects.get(correo="new-admin@example.com")
        self.assertTrue(created.is_staff)
        self.assertTrue(created.is_active)
        self.assertFalse(created.is_superuser)
        self.assertTrue(created.check_password("SafeTemporary2026!"))

    def test_sidebar_displays_the_admin_role(self):
        admin = Usuario.objects.create_superuser(
            correo="owner@example.com", password="TemporaryOwner01"
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("autenticacion:admin_dashboard"))

        self.assertContains(response, "owner@example.com")
        self.assertContains(response, "Superadministrador")

    def test_regular_user_cannot_open_admin_user_management(self):
        user = Usuario.objects.create_user(
            correo="regular@example.com", password="SafeTemporary2026!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("autenticacion:admin_users"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_visible_event(self):
        admin = Usuario.objects.create_superuser(
            correo="events@example.com", password="TemporaryOwner01"
        )
        self.client.force_login(admin)
        image = SimpleUploadedFile(
            "evento.png", b"image-content", content_type="image/png"
        )

        with (
            tempfile.TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
            patch(
                "apps.autenticacion.views.get_boletab_events",
                return_value=[
                    {"id": "81", "name": "Evento Boletab"},
                    {"id": "82", "name": "Segundo evento"},
                ],
            ),
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_create"),
                {
                    "boletab_eventos": ["81", "82"],
                    "nombre": "Festival de prueba",
                    "descripcion": "Descripción del evento.",
                    "imagen": image,
                    "visible": True,
                },
            )

        self.assertRedirects(response, reverse("autenticacion:admin_events"))
        event = Evento.objects.get(nombre="Festival de prueba")
        self.assertTrue(event.visible)
        self.assertEqual(
            event.boletab_eventos,
            [
                {"id": "81", "name": "Evento Boletab"},
                {"id": "82", "name": "Segundo evento"},
            ],
        )
        self.assertEqual(event.descripcion, "Descripción del evento.")

    def test_admin_can_update_event(self):
        admin = Usuario.objects.create_superuser(
            correo="editor@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            boletab_eventos=[{"id": "81", "name": "Evento Boletab"}],
            nombre="Nombre anterior",
            descripcion="Descripción anterior",
            imagen="eventos/existing.png",
            visible=False,
        )
        self.client.force_login(admin)

        with patch(
            "apps.autenticacion.views.get_boletab_events",
            return_value=[{"id": "81", "name": "Evento Boletab"}],
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_update", args=[event.pk]),
                {
                    "boletab_eventos": ["81"],
                    "nombre": "Nombre actualizado",
                    "descripcion": "Descripción actualizada",
                    "visible": True,
                },
            )

        self.assertRedirects(response, reverse("autenticacion:admin_events"))
        event.refresh_from_db()
        self.assertEqual(event.nombre, "Nombre actualizado")
        self.assertTrue(event.visible)

    def test_regular_user_cannot_open_event_management(self):
        user = Usuario.objects.create_user(
            correo="visitor@example.com", password="SafeTemporary2026!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("autenticacion:admin_events"))

        self.assertEqual(response.status_code, 403)

    def test_spaces_view_is_enabled_for_linked_event(self):
        admin = Usuario.objects.create_superuser(
            correo="spaces@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            boletab_eventos=[{"id": "61", "name": "Evento Boletab"}],
            nombre="Evento con espacios",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)

        with patch(
            "apps.autenticacion.views.get_boletab_places",
            return_value=[
                {
                    "asientoId": 59349,
                    "etiqueta": "Hacienda 1",
                    "seccionNombre": "Area 1",
                    "categoriaNombre": "Hacienda",
                    "estado": "DISPONIBLE",
                    "precio": 35000.61,
                    "habilitado": True,
                    "points": "175,292 202,292 202,315 175,315",
                    "coordinates": [
                        (175.0, 292.0),
                        (202.0, 292.0),
                        (202.0, 315.0),
                        (175.0, 315.0),
                    ],
                    "color": "#3B82F6",
                    "posX": 189.0,
                    "posY": 304.0,
                    "numero": 1,
                }
            ],
        ):
            response = self.client.get(
                reverse("autenticacion:admin_event_spaces", args=[event.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuración de espacios")
        self.assertContains(response, "Evento Boletab")
        self.assertContains(response, "175,292 202,292 202,315 175,315")
        self.assertContains(response, "Hacienda 1")

    def test_spaces_view_redirects_when_event_has_no_boletab_relation(self):
        admin = Usuario.objects.create_superuser(
            correo="spaces-owner@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            nombre="Evento sin relación",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("autenticacion:admin_event_spaces", args=[event.pk])
        )

        self.assertRedirects(
            response,
            reverse("autenticacion:admin_event_update", args=[event.pk]),
        )

    def test_admin_can_save_eligibility_rules_for_space(self):
        admin = Usuario.objects.create_superuser(
            correo="rules@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            boletab_eventos=[{"id": "61", "name": "Evento Boletab"}],
            nombre="Evento con reglas",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)
        place = {
            "asientoId": 59349,
            "etiqueta": "Hacienda 1",
            "coordinates": [(175.0, 292.0), (202.0, 292.0), (202.0, 315.0)],
        }

        with patch(
            "apps.autenticacion.views.get_boletab_places", return_value=[place]
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_spaces", args=[event.pk]),
                {
                    "boletab_evento_id": "61",
                    "asiento_id": "59349",
                    "etiqueta": "Hacienda 1",
                    "reglas_json": json.dumps(
                        [
                            {"giro": "ARTESANIAS", "subgiro": "TEXTILES"},
                            {"giro": "TURISMO_EXPERIENCIAS", "subgiro": "TOURS"},
                        ]
                    ),
                    "folios": "FOLIO-01\nfolio-02",
                },
            )

        self.assertEqual(response.status_code, 302)
        rule = ReglaEspacio.objects.get(evento=event, asiento_id="59349")
        self.assertEqual(
            rule.reglas,
            [
                {"giro": "ARTESANIAS", "subgiro": "TEXTILES"},
                {"giro": "TURISMO_EXPERIENCIAS", "subgiro": "TOURS"},
            ],
        )
        self.assertEqual(rule.giros, ["ARTESANIAS", "TURISMO_EXPERIENCIAS"])
        self.assertEqual(rule.subgiros, ["TEXTILES", "TOURS"])
        self.assertEqual(rule.folios, ["FOLIO-01", "FOLIO-02"])

    def test_userinfo_keeps_custom_claims_from_id_token(self):
        backend = LlaveTabascoOIDCBackend()
        token_claims = {
            "sub": "llave-123",
            "curp": "RECS020207HTCLLNA4",
            "tipo": "Persona física",
        }
        userinfo = {"sub": "llave-123", "email": "persona@example.com"}

        with self.subTest("custom claims are merged"):
            from unittest.mock import patch

            with patch(
                "mozilla_django_oidc.auth.OIDCAuthenticationBackend.get_userinfo",
                return_value=userinfo,
            ):
                claims = backend.get_userinfo("access", "id", token_claims)

        self.assertEqual(claims["curp"], token_claims["curp"])
        self.assertEqual(claims["tipo"], token_claims["tipo"])
        self.assertEqual(claims["email"], userinfo["email"])

    def test_oidc_claims_are_logged_as_complete_json(self):
        claims = {
            "sub": "llave-123",
            "name": "SANTIAGO REAL",
            "custom_claim": {"roles": ["ciudadano"]},
        }

        with self.settings(OIDC_LOG_CLAIMS=True):
            with self.assertLogs("apps.autenticacion.oidc", level="WARNING") as logs:
                _log_oidc_claims(claims)

        output = "\n".join(logs.output)
        self.assertIn('"custom_claim": {', output)
        self.assertIn('"roles": [', output)
        self.assertIn('"sub": "llave-123"', output)

    def test_login_only_offers_llave_tabasco(self):
        client = Client()
        response = client.get(reverse("autenticacion:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("oidc_authentication_init"))
        self.assertNotContains(response, "password")
        self.assertEqual(client.post(reverse("autenticacion:login")).status_code, 405)
        with self.assertRaises(NoReverseMatch):
            reverse("autenticacion:register")

    def test_reused_oidc_callback_redirects_to_login(self):
        client = Client()
        session = client.session
        session["oidc_states"] = {
            "another-state": {"nonce": "nonce", "code_verifier": None}
        }
        session.save()

        response = client.get(
            reverse("oidc_authentication_callback"),
            {"state": "already-used-state", "code": "already-used-code"},
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("autenticacion:login"))
        follow_up = client.get(
            reverse("autenticacion:login"), HTTP_HOST="localhost:8000"
        )
        self.assertContains(follow_up, "ya fue utilizado o expiró")

    def test_oidc_claims_populate_general_data(self):
        claims = {
            "sub": "llave-123",
            "given_name": "SANTIAGO",
            "family_name": "REAL",
            "apellido_materno": "CALCANEO",
            "name": "SANTIAGO REAL",
            "email": "sanntiarealcalcaneo@gmail.com",
            "curp": "RECS020207HTCLLNA4",
            "tipo": "Persona física",
        }
        user = LlaveTabascoOIDCBackend().create_user(claims)
        datos = DatosGenerales.objects.get(expediente=user.expediente)
        self.assertEqual(datos.nombres, "SANTIAGO")
        self.assertEqual(datos.apellido_paterno, "REAL")
        self.assertEqual(datos.apellido_materno, "CALCANEO")
        self.assertEqual(datos.correo_contacto, claims["email"])
        self.assertEqual(datos.curp, claims["curp"])
        self.assertEqual(
            user.expediente.tipo_persona, "PERSONA_FISICA"
        )

    def test_oidc_login_replaces_provisional_email_with_claim_email(self):
        user = Usuario.objects.create(
            correo="llave-123@llave-tabasco.local",
            oidc_sub="llave-123",
            nombre_visible="Nombre anterior",
        )
        claims = {
            "sub": "llave-123",
            "name": "SANTIAGO REAL",
            "email": "realcalcaneosantiago@gmail.com",
        }

        LlaveTabascoOIDCBackend().update_user(user, claims)

        user.refresh_from_db()
        self.assertEqual(user.correo, claims["email"])
        self.assertEqual(user.nombre_visible, claims["name"])
