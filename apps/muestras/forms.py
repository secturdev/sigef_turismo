from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from apps.expediente.models import Mobiliario, Producto
from apps.expediente.validators import validate_document_file

from .constants import GIROS, PROGRAMAS_ESPECIALES, SUBGIROS, SUBGIROS_POR_GIRO

INPUT_CLASS = "form-input"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_equipment_image(uploaded) -> None:
    name = (uploaded.name or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Sube una imagen JPG, PNG o WEBP.")
    if uploaded.size and uploaded.size > MAX_IMAGE_SIZE:
        raise ValidationError("La imagen no puede superar 5 MB.")


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


def _style(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(
            field.widget,
            (forms.RadioSelect, forms.CheckboxInput, forms.FileInput, forms.ClearableFileInput),
        ):
            if isinstance(field.widget, (forms.FileInput, forms.ClearableFileInput)):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{existing} {INPUT_CLASS}".strip()
            continue
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{existing} {INPUT_CLASS}".strip()


class Paso1Form(forms.Form):
    giro = forms.ChoiceField(label="Giro", choices=GIROS)
    subgiro = forms.ChoiceField(label="Subgiro", choices=SUBGIROS)
    programa_especial = forms.ChoiceField(
        label="¿Perteneces a un programa social?",
        choices=PROGRAMAS_ESPECIALES,
        widget=forms.RadioSelect,
        required=False,
    )
    def __init__(self, *args, expediente=None, solicitud=None, evento_categoria="", **kwargs):
        super().__init__(*args, **kwargs)
        self.expediente = expediente
        self.solicitud = solicitud
        self.evento_categoria = evento_categoria
        self.product_rows = []
        self.furniture_rows = []
        self.fields["folio_programa_social"] = forms.CharField(
            label="Folio del programa", max_length=100, required=False,
            help_text="Obligatorio si perteneces a un programa social.",
        )
        from apps.landingpage.models import Evento
        from django.utils.text import slugify
        
        # Get active event to read dynamic equipment
        evento = Evento.objects.filter(visible=True).first()
        self.equipos_dinamicos = []
        if evento and evento.equipamiento_obligatorio:
            # We assume it is a list of dicts like [{"nombre": "Sillas", "pedir_foto": True}]
            for eq in evento.equipamiento_obligatorio:
                eq_nombre = eq.get("nombre", "")
                if not eq_nombre: continue
                eq_slug = slugify(eq_nombre).replace("-", "_")
                
                
                # Fetch existing value if editing
                existing_qty = 1
                existing_mod = ""
                existing_pic = False
                if solicitud:
                    # Look up in EquipamientoAdicionalSolicitud
                    eq_obj = solicitud.detalle_equipamiento_adicional.filter(nombre_equipo=eq_nombre).first()
                    if eq_obj:
                        existing_qty = eq_obj.cantidad
                        existing_mod = eq_obj.modelo
                        existing_pic = bool(eq_obj.foto)

                self.fields[f"eq_qty_{eq_slug}"] = forms.IntegerField(
                    label=f"Cantidad de {eq_nombre}", min_value=1, initial=existing_qty
                )
                self.fields[f"eq_mod_{eq_slug}"] = forms.CharField(
                    label=f"Nombre o modelo de {eq_nombre}", max_length=150, required=False, initial=existing_mod
                )
                if eq.get("pedir_foto", False):
                    self.fields[f"eq_pic_{eq_slug}"] = forms.FileField(
                        label=f"Foto de {eq_nombre}",
                        required=not existing_pic,
                        validators=[validate_equipment_image],
                        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"}),
                        help_text="JPG, PNG o WEBP (máx. 5 MB).",
                    )
                self.equipos_dinamicos.append({
                    "slug": eq_slug,
                    "nombre": eq_nombre,
                    "pedir_foto": eq.get("pedir_foto", False),
                    "qty_field": self[f"eq_qty_{eq_slug}"],
                    "mod_field": self[f"eq_mod_{eq_slug}"],
                    "pic_field": self[f"eq_pic_{eq_slug}"] if eq.get("pedir_foto", False) else None,
                    "existing_pic_url": eq_obj.foto.url if (solicitud and eq_obj and eq_obj.foto) else None
                })
        if expediente is not None:
            selected_products = {
                item.producto_id: item for item in solicitud.detalle_productos.all()
            } if solicitud else {}
            for product in expediente.productos.all():
                detail = selected_products.get(product.pk)
                select_name = f"product_{product.pk}"
                stock_name = f"product_{product.pk}_stock"
                price_name = f"product_{product.pk}_price"
                invoice_name = f"product_{product.pk}_invoice"
                self.fields[select_name] = forms.BooleanField(required=False)
                self.fields[stock_name] = forms.IntegerField(required=False, min_value=1, label="Stock total")
                self.fields[price_name] = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Precio de venta")
                if not product.factura:
                    self.fields[invoice_name] = forms.FileField(required=False, label="Factura (PDF)", help_text="Opcional, máximo 10 MB.", validators=[validate_document_file], widget=forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}))
                if detail:
                    self.initial.update({select_name: True, stock_name: detail.stock_total, price_name: detail.precio_venta})
                self.product_rows.append({"item": product, "select": self[select_name], "stock": self[stock_name], "price": self[price_name], "invoice": self[invoice_name] if invoice_name in self.fields else None})

            self.fields["producto_principal"] = forms.ChoiceField(
                label="Producto principal",
                choices=[(str(product.pk), product.nombre) for product in expediente.productos.all()],
                widget=forms.RadioSelect,
            )
            if solicitud and solicitud.producto_principal_id:
                self.initial["producto_principal"] = str(solicitud.producto_principal_id)
            elif expediente.productos.filter(es_principal=True).exists():
                self.initial["producto_principal"] = str(
                    expediente.productos.filter(es_principal=True).values_list("pk", flat=True).first()
                )

            selected_furniture = {
                item.mobiliario_id: item for item in solicitud.detalle_mobiliario.all()
            } if solicitud else {}
            for furniture in expediente.mobiliario.all():
                detail = selected_furniture.get(furniture.pk)
                select_name = f"furniture_{furniture.pk}"
                quantity_name = f"furniture_{furniture.pk}_quantity"
                invoice_name = f"furniture_{furniture.pk}_invoice"
                self.fields[select_name] = forms.BooleanField(required=False)
                self.fields[quantity_name] = forms.IntegerField(required=False, min_value=1, label="Cantidad")
                if not furniture.factura:
                    self.fields[invoice_name] = forms.FileField(required=False, label="Factura (PDF)", help_text="Opcional, máximo 10 MB.", validators=[validate_document_file], widget=forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}))
                if detail:
                    self.initial.update({select_name: True, quantity_name: detail.cantidad})
                self.furniture_rows.append({"item": furniture, "select": self[select_name], "quantity": self[quantity_name], "invoice": self[invoice_name] if invoice_name in self.fields else None})
        _style(self)

    def clean(self):
        cleaned = super().clean()
        giro = cleaned.get("giro")
        subgiro = cleaned.get("subgiro")
        valid_subgiros = {value for value, _ in SUBGIROS_POR_GIRO.get(giro, [])}
        if subgiro and subgiro not in valid_subgiros:
            self.add_error("subgiro", "Selecciona un subgiro correspondiente al giro elegido.")
        prog_esp = cleaned.get("programa_especial")
        if prog_esp and prog_esp != "NINGUNO" and not (cleaned.get("folio_programa_social") or "").strip():
            self.add_error("folio_programa_social", "Ingresa el folio del programa social.")
        selected_products = []
        for row in self.product_rows:
            pk = row["item"].pk
            if cleaned.get(f"product_{pk}"):
                if not cleaned.get(f"product_{pk}_stock"):
                    self.add_error(f"product_{pk}_stock", "Indica la cantidad de stock.")
                if cleaned.get(f"product_{pk}_price") is None:
                    self.add_error(f"product_{pk}_price", "Indica el precio de venta.")
                selected_products.append(row["item"])
        if not selected_products:
            raise forms.ValidationError("Selecciona al menos un producto de tu catálogo.")
        principal_id = cleaned.get("producto_principal")
        if principal_id and str(principal_id) not in {str(item.pk) for item in selected_products}:
            self.add_error("producto_principal", "El producto principal también debe estar seleccionado para el evento.")

        selected_furniture = [row["item"] for row in self.furniture_rows if cleaned.get(f"furniture_{row['item'].pk}")]
        for item in selected_furniture:
            if not cleaned.get(f"furniture_{item.pk}_quantity"):
                self.add_error(f"furniture_{item.pk}_quantity", "Indica la cantidad.")
        return cleaned

    def participation_details(self):
        products = []
        for row in self.product_rows:
            item = row["item"]
            if self.cleaned_data.get(f"product_{item.pk}"):
                products.append({"item": item, "stock": self.cleaned_data[f"product_{item.pk}_stock"], "price": self.cleaned_data[f"product_{item.pk}_price"], "invoice": self.cleaned_data.get(f"product_{item.pk}_invoice")})
        furniture = []
        for row in self.furniture_rows:
            item = row["item"]
            if self.cleaned_data.get(f"furniture_{item.pk}"):
                furniture.append({"item": item, "quantity": self.cleaned_data[f"furniture_{item.pk}_quantity"], "invoice": self.cleaned_data.get(f"furniture_{item.pk}_invoice")})
        equipos = []
        if hasattr(self, 'equipos_dinamicos'):
            for eq in self.equipos_dinamicos:
                slug = eq["slug"]
                equipos.append({
                    "nombre_equipo": eq["nombre"],
                    "cantidad": self.cleaned_data.get(f"eq_qty_{slug}", 1),
                    "modelo": self.cleaned_data.get(f"eq_mod_{slug}", ""),
                    "foto": self.cleaned_data.get(f"eq_pic_{slug}")
                })
        return products, furniture, equipos


class Paso2Form(forms.Form):
    logo = forms.FileField(
        label="Logo del comercio",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"}
        ),
    )
    imagenes = forms.FileField(
        label="Imágenes del comercio",
        required=False,
        widget=MultipleFileInput(
            attrs={
                "accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].help_text = "JPG, PNG o WEBP. Máx. 5 MB."
        self.fields["imagenes"].help_text = "Puedes seleccionar varias (máx. 5 en total)."
        _style(self)
