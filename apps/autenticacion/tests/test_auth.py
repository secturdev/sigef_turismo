import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from apps.autenticacion.models import Usuario
from apps.autenticacion.forms import SpaceRuleForm
from apps.autenticacion.oidc import LlaveTabascoOIDCBackend, _log_oidc_claims
from apps.expediente.models import DatosGenerales
from apps.landingpage.models import Evento, ReglaEspacio, ReglaSeccion
from apps.landingpage.boletab import BoletabError
from apps.muestras.models import SolicitudMuestra

import tempfile
from unittest.mock import patch


class AuthTests(TestCase):
    def test_exhibitor_events_only_show_visible_database_events(self):
        user = Usuario.objects.create_user(
            correo="events-user@example.com", password="TemporaryOwner01"
        )
        visible_event = Evento.objects.create(
            nombre="Encuentro artesanal",
            descripcion="Evento publicado",
            imagen="eventos/publicado.png",
            visible=True,
        )
        Evento.objects.create(
            nombre="Evento oculto",
            descripcion="No publicado",
            imagen="eventos/oculto.png",
            visible=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("expediente:events"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Encuentro artesanal")
        self.assertNotContains(response, "Evento oculto")
        self.assertNotContains(response, "Expo Navideña")
        self.assertContains(response, f"?evento={visible_event.pk}")

    def test_available_spaces_api_filters_by_application_access_type(self):
        admin = Usuario.objects.create_superuser(
            correo="api-admin@example.com", password="TemporaryOwner01"
        )
        applicant = Usuario.objects.create_user(
            correo="applicant@example.com", password="TemporaryOwner01"
        )
        solicitud = SolicitudMuestra.objects.create(
            usuario=applicant,
            giro="ARTESANIAS",
            subgiro="TEXTILES",
            programa_especial="NINGUNO",
        )
        event = Evento.objects.create(
            nombre="Evento API",
            descripcion="Descripción",
            imagen="eventos/existing.png",
            boletab_eventos=[{"id": "61", "name": "Evento Boletab"}],
            catalogo_folios=[
                {"codigo": "SOCIAL-001", "tipo": "PROGRAMA_SOCIAL"}
            ],
        )
        ReglaEspacio.objects.create(
            evento=event,
            boletab_evento_id="61",
            asiento_id="100",
            etiqueta="Giro",
            reglas=[{"giro": "ARTESANIAS", "subgiro": "TEXTILES"}],
            giros=["ARTESANIAS"],
            subgiros=["TEXTILES"],
        )
        ReglaEspacio.objects.create(
            evento=event,
            boletab_evento_id="61",
            asiento_id="200",
            etiqueta="Social",
            folios=["SOCIAL-001"],
        )
        ReglaSeccion.objects.create(
            evento=event,
            boletab_evento_id="61",
            seccion_id="376",
            seccion_nombre="Artesanos",
            reglas=[{"giro": "ARTESANIAS", "subgiro": "TEXTILES", "cantidad": 10}],
        )
        places = [
            {"asientoId": 100, "etiqueta": "Giro", "estado": "DISPONIBLE", "habilitado": True},
            {"asientoId": 200, "etiqueta": "Social", "estado": "DISPONIBLE", "habilitado": True},
            {"asientoId": 300, "seccionId": 376, "etiqueta": "Sección", "estado": "DISPONIBLE", "habilitado": True},
        ]
        url = reverse(
            "autenticacion:api_available_spaces", args=[event.pk, applicant.pk]
        )
        unauthorized_response = self.client.get(url)
        self.client.force_login(admin)

        with patch(
            "apps.landingpage.services.space_eligibility.get_boletab_places",
            return_value=places,
        ):
            giro_response = self.client.get(url)
            solicitud.folio_programa_social = "SOCIAL-001"
            solicitud.programa_especial = "ORIGEN_TABASCO"
            solicitud.save()
            folio_response = self.client.get(url)

        self.assertEqual(giro_response.status_code, 200)
        self.assertEqual(unauthorized_response.status_code, 401)
        self.assertEqual(giro_response.json()["criterio"]["tipo"], "GIRO_SUBGIRO")
        self.assertEqual(
            {item["asiento_id"] for item in giro_response.json()["espacios"]},
            {"100", "300"},
        )
        section_space = next(
            item for item in giro_response.json()["espacios"] if item["asiento_id"] == "300"
        )
        self.assertEqual(section_space["capacidad_seccion"], 10)
        self.assertEqual(folio_response.json()["criterio"]["tipo"], "FOLIO")
        self.assertTrue(folio_response.json()["criterio"]["folio_valido"])
        self.assertEqual(folio_response.json()["espacios"][0]["asiento_id"], "200")

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
                    "giros_disponibles": ["ARTESANIAS", "TURISMO_EXPERIENCIAS"],
                    "subgiros_disponibles": ["TEXTILES", "TOURS"],
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
        self.assertEqual(
            event.giros_disponibles, ["ARTESANIAS", "TURISMO_EXPERIENCIAS"]
        )
        self.assertEqual(event.subgiros_disponibles, ["TEXTILES", "TOURS"])

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
            side_effect=BoletabError("Boletab temporalmente inaccesible"),
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_update", args=[event.pk]),
                {
                    "boletab_eventos": ["81"],
                    "giros_disponibles": ["ARTESANIAS"],
                    "subgiros_disponibles": ["TEXTILES"],
                    "nombre": "Nombre actualizado",
                    "descripcion": "Descripción actualizada",
                    "visible": True,
                },
            )

        self.assertRedirects(response, reverse("autenticacion:admin_events"))
        event.refresh_from_db()
        self.assertEqual(event.nombre, "Nombre actualizado")
        self.assertTrue(event.visible)
        self.assertEqual(event.giros_disponibles, ["ARTESANIAS"])
        self.assertEqual(event.subgiros_disponibles, ["TEXTILES"])

    def test_admin_can_create_event_with_described_giro_catalog(self):
        admin = Usuario.objects.create_superuser(
            correo="catalog-editor@example.com", password="TemporaryOwner01"
        )
        self.client.force_login(admin)
        image = SimpleUploadedFile("evento.png", b"image-content", content_type="image/png")
        catalog = [{
            "nombre": "Artesanías regionales",
            "descripcion": "Productos elaborados por artesanos locales.",
            "subgiros": [{
                "nombre": "Textiles bordados",
                "descripcion": "Prendas y accesorios bordados a mano.",
            }],
        }]
        folios = [
            {"codigo": " social-2026-001 ", "tipo": "programa_social"},
            {"codigo": "PATROCINADOR-01", "tipo": "PATROCINADOR"},
        ]
        with (
            tempfile.TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
            patch("apps.autenticacion.views.get_boletab_events", return_value=[{"id": "81", "name": "Evento Boletab"}]),
        ):
            response = self.client.post(reverse("autenticacion:admin_event_create"), {
                "boletab_eventos": ["81"], "catalogo_giros": json.dumps(catalog),
                "catalogo_folios": json.dumps(folios),
                "nombre": "Evento con catálogo", "descripcion": "Descripción", "imagen": image,
            })
        self.assertRedirects(response, reverse("autenticacion:admin_events"))
        event = Evento.objects.get(nombre="Evento con catálogo")
        self.assertEqual(event.catalogo_giros[0]["id"], "ARTESANIAS_REGIONALES")
        self.assertEqual(event.catalogo_giros[0]["subgiros"][0]["descripcion"], "Prendas y accesorios bordados a mano.")
        self.assertEqual(
            event.catalogo_folios,
            [
                {"codigo": "SOCIAL-2026-001", "tipo": "PROGRAMA_SOCIAL"},
                {"codigo": "PATROCINADOR-01", "tipo": "PATROCINADOR"},
            ],
        )

    def test_admin_can_fetch_boletab_events_as_json(self):
        admin = Usuario.objects.create_superuser(
            correo="catalog-fetch@example.com", password="TemporaryOwner01"
        )
        self.client.force_login(admin)

        with patch(
            "apps.autenticacion.views.get_boletab_events",
            return_value=[{"id": "61", "name": "Evento Boletab"}],
        ):
            response = self.client.get(
                reverse("autenticacion:admin_boletab_events_data")
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"events": [{"id": "61", "name": "Evento Boletab"}]},
        )

    def test_event_rejects_subgiro_from_unselected_giro(self):
        admin = Usuario.objects.create_superuser(
            correo="catalog@example.com", password="TemporaryOwner01"
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
                return_value=[{"id": "81", "name": "Evento Boletab"}],
            ),
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_create"),
                {
                    "boletab_eventos": ["81"],
                    "giros_disponibles": ["ARTESANIAS"],
                    "subgiros_disponibles": ["TOURS"],
                    "nombre": "Evento inválido",
                    "descripcion": "Descripción",
                    "imagen": image,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Cada subgiro debe corresponder a uno de los giros seleccionados.",
        )
        self.assertFalse(Evento.objects.filter(nombre="Evento inválido").exists())

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
            catalogo_giros=[{
                "id": "ARTESANIAS",
                "nombre": "Artesanías",
                "descripcion": "Productos artesanales",
                "subgiros": [{"id": "TEXTILES", "nombre": "Textiles", "descripcion": "Textiles"}],
            }],
            nombre="Evento con espacios",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)

        page_response = self.client.get(
            reverse("autenticacion:admin_event_spaces", args=[event.pk])
        )
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Configuración de espacios")
        self.assertContains(page_response, "Evento Boletab")

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
                reverse("autenticacion:admin_event_spaces_data", args=[event.pk]),
                {"evento": "61"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["places"][0]["asientoId"], 59349)
        self.assertEqual(payload["places"][0]["etiqueta"], "Hacienda 1")
        self.assertEqual(payload["configured_count"], 0)
        self.assertEqual(payload["view_box"]["width"], 100)

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

    def test_admin_can_fetch_sections_for_linked_boletab_event(self):
        admin = Usuario.objects.create_superuser(
            correo="sections@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            boletab_eventos=[{"id": "61", "name": "Evento Boletab"}],
            catalogo_giros=[{
                "id": "ARTESANIAS",
                "nombre": "Artesanías",
                "descripcion": "Productos artesanales",
                "subgiros": [{"id": "TEXTILES", "nombre": "Textiles", "descripcion": "Textiles"}],
            }],
            nombre="Evento con secciones",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)

        with patch(
            "apps.autenticacion.views.get_boletab_sections",
            return_value=[
                {
                    "id": 376,
                    "nombre": "Chocolaterías y Bebidas",
                    "tipo": "POLIGONOS",
                    "totalLugares": 9,
                }
            ],
        ):
            response = self.client.get(
                reverse("autenticacion:admin_event_sections_data", args=[event.pk]),
                {"evento": "61"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sections"][0]["id"], 376)

        with (
            patch(
                "apps.autenticacion.views.get_boletab_sections",
                return_value=[{"id": 376, "nombre": "Chocolaterías y Bebidas"}],
            ),
            patch(
                "apps.autenticacion.views.get_boletab_places",
                return_value=[{"asientoId": value} for value in range(1, 10)],
            ),
        ):
            save_response = self.client.post(
                reverse("autenticacion:admin_event_sections_data", args=[event.pk]),
                {
                    "boletab_evento_id": "61",
                    "seccion_id": "376",
                    "reglas_json": json.dumps([{
                        "giro": "ARTESANIAS", "subgiro": "TEXTILES", "cantidad": 7,
                    }]),
                },
            )

        self.assertEqual(save_response.status_code, 200)
        section_rule = ReglaSeccion.objects.get(evento=event, seccion_id="376")
        self.assertEqual(section_rule.reglas[0]["cantidad"], 7)

        for asiento_id in ("1", "2", "3"):
            ReglaEspacio.objects.create(
                evento=event,
                boletab_evento_id="61",
                asiento_id=asiento_id,
                folios=["PATROCINADOR"],
            )
        with (
            patch(
                "apps.autenticacion.views.get_boletab_sections",
                return_value=[{"id": 376, "nombre": "Chocolaterías y Bebidas"}],
            ),
            patch(
                "apps.autenticacion.views.get_boletab_places",
                return_value=[{"asientoId": value} for value in range(1, 11)],
            ),
        ):
            over_limit_response = self.client.post(
                reverse("autenticacion:admin_event_sections_data", args=[event.pk]),
                {
                    "boletab_evento_id": "61",
                    "seccion_id": "376",
                    "reglas_json": json.dumps([{
                        "giro": "ARTESANIAS", "subgiro": "TEXTILES", "cantidad": 8,
                    }]),
                },
            )
        self.assertEqual(over_limit_response.status_code, 400)
        self.assertEqual(over_limit_response.json()["capacity"]["global_limit"], 7)

        places = [
            {"asientoId": value, "seccionId": 376, "etiqueta": f"Stand {value}"}
            for value in range(1, 11)
        ]
        with patch(
            "apps.autenticacion.views.get_boletab_places", return_value=places
        ):
            individual_response = self.client.post(
                reverse("autenticacion:admin_event_spaces", args=[event.pk]),
                {
                    "boletab_evento_id": "61",
                    "asiento_ids_json": json.dumps(["4"]),
                    "reglas_json": json.dumps([{
                        "giro": "ARTESANIAS", "subgiro": "TEXTILES",
                    }]),
                    "folios": "",
                },
                HTTP_ACCEPT="application/json",
            )
        self.assertEqual(individual_response.status_code, 400)
        self.assertIn("Reduce primero", individual_response.json()["error"])
        self.assertFalse(
            ReglaEspacio.objects.filter(evento=event, asiento_id="4").exists()
        )

    def test_admin_can_save_eligibility_rules_for_space(self):
        admin = Usuario.objects.create_superuser(
            correo="rules@example.com", password="TemporaryOwner01"
        )
        event = Evento.objects.create(
            boletab_eventos=[{"id": "61", "name": "Evento Boletab"}],
            catalogo_folios=[
                {"codigo": "FOLIO-01", "tipo": "PROGRAMA_SOCIAL"},
                {"codigo": "FOLIO-02", "tipo": "PROGRAMA_SOCIAL"},
            ],
            nombre="Evento con reglas",
            descripcion="Descripción",
            imagen="eventos/existing.png",
        )
        self.client.force_login(admin)
        places = [
            {
                "asientoId": 59349,
                "etiqueta": "Hacienda 1",
                "coordinates": [(175.0, 292.0), (202.0, 292.0), (202.0, 315.0)],
            },
            {
                "asientoId": 59350,
                "etiqueta": "Hacienda 2",
                "coordinates": [(205.0, 292.0), (232.0, 292.0), (232.0, 315.0)],
            },
        ]

        with patch(
            "apps.autenticacion.views.get_boletab_places", return_value=places
        ):
            response = self.client.post(
                reverse("autenticacion:admin_event_spaces", args=[event.pk]),
                {
                    "boletab_evento_id": "61",
                    "asiento_ids_json": json.dumps(["59349", "59350"]),
                    "etiqueta": "Hacienda 1",
                    "reglas_json": json.dumps(
                        [
                            {"giro": "ARTESANIAS", "subgiro": "TEXTILES"},
                            {"giro": "TURISMO_EXPERIENCIAS", "subgiro": "TOURS"},
                        ]
                    ),
                    "folios": "",
                },
                HTTP_ACCEPT="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saved_count"], 2)
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
        self.assertEqual(rule.folios, [])
        second_rule = ReglaEspacio.objects.get(evento=event, asiento_id="59350")
        self.assertEqual(second_rule.reglas, rule.reglas)
        self.assertEqual(second_rule.folios, rule.folios)

        clear_response = self.client.post(
            reverse("autenticacion:admin_event_spaces", args=[event.pk]),
            {
                "action": "clear_space_rules",
                "boletab_evento_id": "61",
                "asiento_ids_json": json.dumps(["59349", "59350"]),
            },
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(clear_response.status_code, 200)
        self.assertEqual(clear_response.json()["deleted_count"], 2)
        self.assertFalse(ReglaEspacio.objects.filter(evento=event).exists())

    def test_space_rule_rejects_combining_giros_and_folios(self):
        form = SpaceRuleForm(
            {
                "boletab_evento_id": "61",
                "asiento_ids_json": json.dumps(["59349"]),
                "reglas_json": json.dumps(
                    [{"giro": "ARTESANIAS", "subgiro": "TEXTILES"}]
                ),
                "folios": "SOCIAL-001",
            },
            folio_catalog=[
                {"codigo": "SOCIAL-001", "tipo": "PROGRAMA_SOCIAL"}
            ],
        )

        self.assertFalse(form.is_valid())
        self.assertIn("no por ambos", form.non_field_errors()[0])

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
