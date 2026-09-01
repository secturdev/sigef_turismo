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
                "programa_especial": "ORIGEN_TABASCO",
                "cantidad_botes_basura": "2",
                "cantidad_extintores": "1",
                f"product_{self.product.pk}": "on",
                f"product_{self.product.pk}_stock": "120",
                f"product_{self.product.pk}_price": "85.50",
                f"furniture_{self.furniture.pk}": "on",
                f"furniture_{self.furniture.pk}_quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        product_detail = ProductoSolicitud.objects.get(producto=self.product)
        furniture_detail = MobiliarioSolicitud.objects.get(mobiliario=self.furniture)
        self.assertEqual(product_detail.stock_total, 120)
        self.assertEqual(str(product_detail.precio_venta), "85.50")
        self.assertEqual(furniture_detail.cantidad, 2)
        self.assertEqual(product_detail.solicitud.cantidad_botes_basura, 2)
        self.assertEqual(product_detail.solicitud.cantidad_extintores, 1)
