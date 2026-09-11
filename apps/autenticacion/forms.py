import json
import re
import unicodedata

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
    catalogo_giros = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Evento
        fields = (
            "boletab_eventos",
            "catalogo_giros",
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
            self.initial["catalogo_giros"] = json.dumps(
                self.instance.catalogo_giros or self._legacy_catalog(), ensure_ascii=False
            )
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

    @staticmethod
    def _key(value):
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")

    def _legacy_catalog(self):
        giros = self.data.getlist("giros_disponibles") if self.is_bound else self.instance.giros_disponibles
        selected = self.data.getlist("subgiros_disponibles") if self.is_bound else self.instance.subgiros_disponibles
        return [{
            "id": giro, "nombre": dict(GIROS).get(giro, giro), "descripcion": "Descripción pendiente",
            "subgiros": [{"id": sid, "nombre": dict(SUBGIROS_POR_GIRO.get(giro, [])).get(sid, sid), "descripcion": "Descripción pendiente"}
                         for sid in selected if sid in dict(SUBGIROS_POR_GIRO.get(giro, []))],
        } for giro in giros]

    def clean_catalogo_giros(self):
        raw = self.cleaned_data.get("catalogo_giros")
        if not raw and self.is_bound:
            giros = set(self.data.getlist("giros_disponibles"))
            valid_subgiros = {sid for giro in giros for sid, _ in SUBGIROS_POR_GIRO.get(giro, [])}
            if set(self.data.getlist("subgiros_disponibles")) - valid_subgiros:
                raise forms.ValidationError("Cada subgiro debe corresponder a uno de los giros seleccionados.")
        try:
            catalog = json.loads(raw) if raw else self._legacy_catalog()
        except (TypeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError("El catálogo de giros no es válido.") from exc
        if not isinstance(catalog, list) or not catalog:
            raise forms.ValidationError("Agrega al menos un giro.")
        result, used_giros = [], set()
        for giro in catalog:
            if not isinstance(giro, dict):
                raise forms.ValidationError("La información de un giro no es válida.")
            nombre, descripcion = str(giro.get("nombre") or "").strip(), str(giro.get("descripcion") or "").strip()
            if not nombre or not descripcion:
                raise forms.ValidationError("Cada giro debe tener nombre y descripción.")
            giro_id = self._key(str(giro.get("id") or nombre))
            if not giro_id or giro_id in used_giros:
                raise forms.ValidationError("Los nombres de los giros deben ser diferentes.")
            used_giros.add(giro_id)
            subgiros, used_subgiros = [], set()
            for subgiro in giro.get("subgiros") or []:
                if not isinstance(subgiro, dict):
                    raise forms.ValidationError("La información de un subgiro no es válida.")
                subnombre, subdescripcion = str(subgiro.get("nombre") or "").strip(), str(subgiro.get("descripcion") or "").strip()
                if not subnombre or not subdescripcion:
                    raise forms.ValidationError("Cada subgiro debe tener nombre y descripción.")
                subgiro_id = self._key(str(subgiro.get("id") or subnombre))
                if not subgiro_id or subgiro_id in used_subgiros:
                    raise forms.ValidationError(f'Los subgiros de "{nombre}" deben tener nombres diferentes.')
                used_subgiros.add(subgiro_id)
                subgiros.append({"id": subgiro_id, "nombre": subnombre, "descripcion": subdescripcion})
            if not subgiros:
                raise forms.ValidationError(f'Agrega al menos un subgiro al giro "{nombre}".')
            result.append({"id": giro_id, "nombre": nombre, "descripcion": descripcion, "subgiros": subgiros})
        return result

    def save(self, commit=True):
        event = super().save(commit=False)
        selected_ids = set(self.cleaned_data["boletab_eventos"])
        event.boletab_eventos = [
            item for item in self.boletab_events if item["id"] in selected_ids
        ]
        event.catalogo_giros = self.cleaned_data["catalogo_giros"]
        event.giros_disponibles = [giro["id"] for giro in event.catalogo_giros]
        event.subgiros_disponibles = [subgiro["id"] for giro in event.catalogo_giros for subgiro in giro["subgiros"]]
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

    def __init__(self, *args, catalog=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog = catalog
        self.fields["folios"].widget.attrs["x-model"] = "selected.foliosText"

    def clean_reglas_json(self):
        raw_value = self.cleaned_data.get("reglas_json") or "[]"
        try:
            rules = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise forms.ValidationError("Las reglas enviadas no son válidas.") from exc
        if not isinstance(rules, list):
            raise forms.ValidationError("Las reglas enviadas no son válidas.")

        valid_giros = ({giro["id"]: giro for giro in self.catalog} if self.catalog else dict(GIROS))
        cleaned = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise forms.ValidationError("Una regla enviada no es válida.")
            giro = str(rule.get("giro") or "")
            subgiro = str(rule.get("subgiro") or "")
            if giro not in valid_giros:
                raise forms.ValidationError("Selecciona un giro válido en cada regla.")
            valid_subgiros = ({item["id"]: item for item in valid_giros[giro]["subgiros"]}
                              if self.catalog else dict(SUBGIROS_POR_GIRO.get(giro, [])))
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
