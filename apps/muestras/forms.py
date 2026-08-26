from __future__ import annotations

from django import forms

from .constants import GIROS, PROGRAMAS_ESPECIALES

INPUT_CLASS = "form-input"


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
    nombre_comercio = forms.CharField(label="Nombre de comercio", max_length=200)
    giro = forms.ChoiceField(label="Giro", choices=GIROS)
    programa_especial = forms.ChoiceField(
        label="Programa especial",
        choices=PROGRAMAS_ESPECIALES,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self)


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
