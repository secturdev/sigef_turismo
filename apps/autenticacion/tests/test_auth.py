from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

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
