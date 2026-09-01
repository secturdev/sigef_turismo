from django.test import Client, TestCase
from django.urls import reverse

from apps.autenticacion.models import Usuario
from apps.autenticacion.oidc import LlaveTabascoOIDCBackend, _log_oidc_claims
from apps.expediente.models import DatosGenerales


class AuthTests(TestCase):
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

    def test_register_and_login_with_email(self):
        client = Client()
        reg = client.post(
            reverse("autenticacion:register"),
            {
                "correo": "ciudadano@example.com",
                "nombre_visible": "Ana",
                "password1": "ClaveSegura123!",
                "password2": "ClaveSegura123!",
            },
        )
        self.assertEqual(reg.status_code, 302)
        self.assertTrue(Usuario.objects.filter(correo="ciudadano@example.com").exists())

        client.logout()
        response = client.post(
            reverse("autenticacion:login"),
            {
                "username": "ciudadano@example.com",
                "password": "ClaveSegura123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("expediente:dashboard"))

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
