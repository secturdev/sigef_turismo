from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario

INPUT_CLASS = "form-input"


def _style_fields(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        if isinstance(field.widget, (forms.RadioSelect, forms.CheckboxInput)):
            continue
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{existing} {INPUT_CLASS}".strip()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ("correo", "nombre_visible")
        labels = {
            "correo": "Correo electrónico",
            "nombre_visible": "Nombre (opcional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    def clean_correo(self):
        return Usuario.objects.normalize_email(self.cleaned_data["correo"])

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2"):
            if cleaned["password1"] != cleaned["password2"]:
                self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico")
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Correo o contraseña incorrectos.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"autocomplete": "email"})
        self.fields["password"].widget.attrs.update(
            {"autocomplete": "current-password"}
        )
        self.fields["password"].label = "Contraseña"
        _style_fields(self)

    def clean(self):
        correo = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if correo and password:
            self.user_cache = authenticate(
                self.request, username=correo, password=password
            )
            if self.user_cache is None:
                raise ValidationError(
                    self.error_messages["invalid_login"],
                    code="invalid_login",
                    params={"username": self.username_field.verbose_name},
                )
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
