from __future__ import annotations

from django import forms

from .models import CampoAdicional, Comercio, Expediente, Mobiliario, Producto
from .validators import validate_curp, validate_document_file, validate_telefono

INPUT_CLASS = "form-input"


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
            continue
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{existing} {INPUT_CLASS}".strip()


class PersonTypeForm(forms.Form):
    tipo_persona = forms.ChoiceField(
        label="Tipo de persona",
        choices=Expediente.TipoPersona.choices,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, identidad_oidc: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if identidad_oidc:
            self.fields["tipo_persona"].disabled = True
            self.fields["tipo_persona"].help_text = (
                "Dato proporcionado por Llave Tabasco; no se puede editar."
            )


class GeneralDataForm(forms.Form):
    nombres = forms.CharField(label="Nombres", max_length=150)
    apellido_paterno = forms.CharField(label="Apellido paterno", max_length=100)
    apellido_materno = forms.CharField(label="Apellido materno", max_length=100)
    curp = forms.CharField(label="CURP", max_length=18)
    telefono = forms.CharField(label="Número de celular", max_length=20)
    correo_contacto = forms.EmailField(label="Correo electrónico")
    representante_legal = forms.CharField(
        label="Representante legal",
        max_length=200,
        required=False,
    )

    def __init__(
        self, *args, tipo_persona: str = "", identidad_oidc: bool = False, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.tipo_persona = tipo_persona
        self.campos_adicionales = list(
            CampoAdicional.objects.filter(activo=True).order_by("orden", "clave")
        )

        if tipo_persona == Expediente.TipoPersona.PERSONA_FISICA:
            self.fields.pop("representante_legal", None)
        elif tipo_persona == Expediente.TipoPersona.PERSONA_MORAL:
            self.fields["nombres"].label = "Razón social"
            self.fields["curp"].label = "CURP del representante legal"
            self.fields["representante_legal"].required = True
            self.fields["representante_legal"].label = "Nombre del representante legal"
            self.fields.pop("apellido_paterno", None)
            self.fields.pop("apellido_materno", None)
            self.fields.pop("telefono", None)
            self.fields.pop("correo_contacto", None)
        elif tipo_persona == Expediente.TipoPersona.CIUDADANO:
            self.fields.pop("representante_legal", None)

        for campo in self.campos_adicionales:
            tipos = campo.tipos_persona or []
            if tipos and tipo_persona not in tipos:
                continue
            key = f"extra_{campo.clave}"
            self.fields[key] = forms.CharField(
                label=campo.etiqueta,
                required=campo.obligatorio,
                max_length=255,
            )

        if identidad_oidc:
            for field_name in (
                "nombres",
                "apellido_paterno",
                "apellido_materno",
                "curp",
                "correo_contacto",
            ):
                if field_name in self.fields:
                    self.fields[field_name].disabled = True
                    self.fields[field_name].help_text = (
                        "Dato proporcionado por Llave Tabasco."
                    )

        _style_fields(self)

    def clean_curp(self):
        return validate_curp(self.cleaned_data.get("curp", ""))

    def clean_telefono(self):
        return validate_telefono(self.cleaned_data.get("telefono", ""))

    def extras_cleaned(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in self.cleaned_data.items():
            if key.startswith("extra_"):
                result[key.removeprefix("extra_")] = value
        return result


class DocumentUploadForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo PDF",
        widget=forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}),
    )
    fecha_emision = forms.DateField(
        label="Fecha de emisión",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vencimiento = forms.DateField(
        label="Fecha de vencimiento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["archivo"].help_text = "Únicamente PDF (máx. 10 MB)."
        _style_fields(self)

    def clean_archivo(self):
        uploaded = self.cleaned_data["archivo"]
        validate_document_file(uploaded)
        return uploaded


class ProductForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("nombre", "imagen", "factura", "descripcion", "es_principal")
        widgets = {
            "imagen": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "factura": forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {"es_principal": "Marcar como producto principal"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["factura"].required = False
        self.fields["factura"].help_text = "Opcional. Únicamente PDF (máx. 10 MB)."
        self.fields["imagen"].help_text = "JPG, PNG o WEBP (máx. 5 MB)."
        _style_fields(self)

    def clean_imagen(self):
        uploaded = self.cleaned_data["imagen"]
        extension = "." + uploaded.name.lower().rsplit(".", 1)[-1] if "." in uploaded.name else ""
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise forms.ValidationError("La imagen debe estar en formato JPG, PNG o WEBP.")
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar 5 MB.")
        return uploaded

    def clean_factura(self):
        uploaded = self.cleaned_data.get("factura")
        if uploaded:
            validate_document_file(uploaded)
        return uploaded


class FurnitureForm(forms.ModelForm):
    class Meta:
        model = Mobiliario
        fields = ("nombre", "imagen", "factura", "descripcion")
        widgets = {
            "imagen": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "factura": forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"}),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["factura"].required = False
        self.fields["factura"].help_text = "Opcional. Únicamente PDF (máx. 10 MB)."
        self.fields["imagen"].help_text = "JPG, PNG o WEBP (máx. 5 MB)."
        _style_fields(self)

    def clean_imagen(self):
        uploaded = self.cleaned_data["imagen"]
        extension = "." + uploaded.name.lower().rsplit(".", 1)[-1] if "." in uploaded.name else ""
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise forms.ValidationError("La imagen debe estar en formato JPG, PNG o WEBP.")
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La imagen no puede superar 5 MB.")
        return uploaded

    def clean_factura(self):
        uploaded = self.cleaned_data.get("factura")
        if uploaded:
            validate_document_file(uploaded)
        return uploaded


class CommerceForm(forms.ModelForm):
    class Meta:
        model = Comercio
        fields = ("nombre", "logo")
        widgets = {
            "logo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].help_text = "JPG, PNG o WEBP (máx. 5 MB)."
        _style_fields(self)

    def clean_logo(self):
        uploaded = self.cleaned_data["logo"]
        extension = "." + uploaded.name.lower().rsplit(".", 1)[-1] if "." in uploaded.name else ""
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise forms.ValidationError("El logo debe estar en formato JPG, PNG o WEBP.")
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El logo no puede superar 5 MB.")
        return uploaded
