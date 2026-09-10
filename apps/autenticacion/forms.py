import json

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import Usuario
from apps.landingpage.models import Evento
from apps.muestras.constants import GIROS, SUBGIROS, SUBGIROS_POR_GIRO


class AdminLoginForm(forms.Form):
    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "nombre@correo.com",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "Contraseña"}
        ),
    )

    error_messages = {
        "invalid_login": "El correo o la contraseña son incorrectos.",
        "not_admin": "Esta cuenta no tiene acceso al panel de administración.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "auth-input"

    def clean(self):
        cleaned_data = super().clean()
        correo = cleaned_data.get("correo")
        password = cleaned_data.get("password")
        if not correo or not password:
            return cleaned_data

        self.user_cache = authenticate(
            self.request, correo=correo, password=password
        )
        if self.user_cache is None:
            raise forms.ValidationError(self.error_messages["invalid_login"])
        if not self.user_cache.is_staff:
            raise forms.ValidationError(self.error_messages["not_admin"])
        return cleaned_data

    def get_user(self):
        return self.user_cache


class AdminCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        help_text="Debe tener al menos 12 caracteres y no ser demasiado común.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password_confirmation = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ("correo", "nombre_visible")
        labels = {"nombre_visible": "Nombre"}
        widgets = {
            "correo": forms.EmailInput(attrs={"autocomplete": "email"}),
            "nombre_visible": forms.TextInput(attrs={"autocomplete": "name"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-input"

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password, self.instance)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("password_confirmation")
        if password and confirmation and password != confirmation:
            self.add_error("password_confirmation", "Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_active = True
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class EventCreateForm(forms.ModelForm):
    boletab_eventos = forms.MultipleChoiceField(
        label="Eventos de Boletab",
        widget=forms.SelectMultiple(attrs={"size": 7}),
        help_text="Puedes seleccionar varios eventos manteniendo presionada la tecla Ctrl.",
    )

    class Meta:
        model = Evento
        fields = (
            "boletab_eventos",
            "nombre",
            "descripcion",
            "imagen",
            "visible",
        )
        labels = {"visible": "Visible para los expositores"}
        help_texts = {
            "imagen": "Formatos permitidos: JPG, PNG o WebP.",
            "visible": "Activa esta opción para publicar el evento.",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Nombre del evento"}),
            "descripcion": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe el evento"}
            ),
        }

    def __init__(self, *args, boletab_events=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.boletab_events = boletab_events or []
        self.fields["boletab_eventos"].choices = [
            (event["id"], event["name"]) for event in self.boletab_events
        ]
        if self.instance and self.instance.pk:
            self.initial["boletab_eventos"] = [
                event["id"] for event in self.instance.boletab_eventos
            ]
        for name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "form-checkbox" if name == "visible" else "form-input"
            )

    def clean_imagen(self):
        imagen = self.cleaned_data["imagen"]
        content_type = getattr(imagen, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("El archivo seleccionado debe ser una imagen.")
        return imagen

    def save(self, commit=True):
        event = super().save(commit=False)
        selected_ids = set(self.cleaned_data["boletab_eventos"])
        event.boletab_eventos = [
            item for item in self.boletab_events if item["id"] in selected_ids
        ]
        if commit:
            event.save()
        return event


class SpaceRuleForm(forms.Form):
    boletab_evento_id = forms.CharField(widget=forms.HiddenInput)
    asiento_id = forms.CharField(widget=forms.HiddenInput)
    etiqueta = forms.CharField(required=False, widget=forms.HiddenInput)
    reglas_json = forms.CharField(required=False, widget=forms.HiddenInput)
    folios = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-input", "rows": 4, "placeholder": "Un folio por línea"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["folios"].widget.attrs["x-model"] = "selected.foliosText"

    def clean_reglas_json(self):
        raw_value = self.cleaned_data.get("reglas_json") or "[]"
        try:
            rules = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError("Las reglas enviadas no son válidas.") from exc
        if not isinstance(rules, list):
            raise forms.ValidationError("Las reglas enviadas no son válidas.")

        valid_giros = dict(GIROS)
        cleaned = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise forms.ValidationError("Una regla enviada no es válida.")
            giro = str(rule.get("giro") or "")
            subgiro = str(rule.get("subgiro") or "")
            if giro not in valid_giros:
                raise forms.ValidationError("Selecciona un giro válido en cada regla.")
            valid_subgiros = dict(SUBGIROS_POR_GIRO.get(giro, []))
            if subgiro and subgiro not in valid_subgiros:
                raise forms.ValidationError("El subgiro no corresponde al giro seleccionado.")
            normalized = {"giro": giro, "subgiro": subgiro}
            if normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned

    def clean_folios(self):
        raw_value = self.cleaned_data["folios"]
        values = raw_value.replace(",", "\n").splitlines()
        return list(dict.fromkeys(value.strip().upper() for value in values if value.strip()))
