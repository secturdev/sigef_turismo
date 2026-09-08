from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.autenticacion.models import Usuario
from apps.expediente.models import Comercio, Expediente, Mobiliario, Producto
from apps.expediente.services import get_or_create_expediente, set_tipo_persona

from .models import MobiliarioSolicitud, ProductoSolicitud


class ParticipationCatalogTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(
            correo="participante@example.com", password="ClaveSegura123!"
        )
        self.expediente = get_or_create_expediente(self.user)
        set_tipo_persona(self.expediente, Expediente.TipoPersona.PERSONA_FISICA)
        image = SimpleUploadedFile("item.jpg", b"imagen", content_type="image/jpeg")
        self.product = Producto.objects.create(
            expediente=self.expediente,
            nombre="Chocolate",
            descripcion="Chocolate artesanal",
            imagen=image,
        )
        self.furniture = Mobiliario.objects.create(
            expediente=self.expediente,
            nombre="Mesa",
            descripcion="Mesa de exhibición",
            imagen=SimpleUploadedFile("mesa.jpg", b"imagen", content_type="image/jpeg"),
        )
        Comercio.objects.create(
            expediente=self.expediente,
            nombre="Cacao Tabasco",
            logo=SimpleUploadedFile("logo.png", b"logo", content_type="image/png"),
        )
        self.client.force_login(self.user)

    def test_application_saves_product_stock_price_and_furniture_quantity(self):
        response = self.client.post(
            reverse("muestras:paso1"),
            {
                "giro": "CHOCOLATE_ARTESANAL",
                "subgiro": "BARRAS_CHOCOLATE",
                "programa_especial": "ORIGEN_TABASCO",
                "folio_programa_social": "OT-2026-001",
                "producto_principal": str(self.product.pk),
                "cantidad_botes_basura": "2",
                "cantidad_extintores": "1",
                "modelo_botes_basura": "Bote plástico 50 L",
                "modelo_extintores": "Extintor ABC 4.5 kg",
                "foto_botes_basura": SimpleUploadedFile("bote.jpg", b"imagen", content_type="image/jpeg"),
                "foto_extintores": SimpleUploadedFile("extintor.png", b"imagen", content_type="image/png"),
                f"product_{self.product.pk}": "on",
                f"product_{self.product.pk}_stock": "120",
                f"product_{self.product.pk}_price": "85.50",
                f"product_{self.product.pk}_invoice": SimpleUploadedFile("factura.pdf", b"%PDF-1.4", content_type="application/pdf"),
                f"furniture_{self.furniture.pk}": "on",
                f"furniture_{self.furniture.pk}_quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        product_detail = ProductoSolicitud.objects.get(producto=self.product)
        furniture_detail = MobiliarioSolicitud.objects.get(mobiliario=self.furniture)
        self.assertEqual(product_detail.stock_total, 120)
        self.assertEqual(str(product_detail.precio_venta), "85.50")
        self.assertTrue(bool(product_detail.factura))
        self.assertEqual(furniture_detail.cantidad, 2)
        self.assertEqual(product_detail.solicitud.cantidad_botes_basura, 2)
        self.assertEqual(product_detail.solicitud.cantidad_extintores, 1)
        self.assertTrue(bool(product_detail.solicitud.foto_botes_basura))
        self.assertTrue(bool(product_detail.solicitud.foto_extintores))
        self.assertEqual(product_detail.solicitud.producto_principal, self.product)
        self.assertEqual(product_detail.solicitud.subgiro, "BARRAS_CHOCOLATE")

    def test_fair_equipment_photos_are_required(self):
        response = self.client.post(
            reverse("muestras:paso1"),
            {
                "giro": "CHOCOLATE_ARTESANAL",
                "subgiro": "BARRAS_CHOCOLATE",
                "programa_especial": "NINGUNO",
                "producto_principal": str(self.product.pk),
                "cantidad_botes_basura": "1",
                "cantidad_extintores": "1",
                "modelo_botes_basura": "Bote 50 L",
                "modelo_extintores": "Extintor ABC",
                f"product_{self.product.pk}": "on",
                f"product_{self.product.pk}_stock": "10",
                f"product_{self.product.pk}_price": "20",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "foto_botes_basura", "Este campo es requerido.")
        self.assertFormError(response.context["form"], "foto_extintores", "Este campo es requerido.")
