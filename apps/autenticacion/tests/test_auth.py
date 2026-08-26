from django.test import Client, TestCase
from django.urls import reverse

from apps.autenticacion.models import Usuario


class AuthTests(TestCase):
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
