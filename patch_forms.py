import io
import re

with io.open('apps/muestras/forms.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make programa_especial required=False
content = content.replace(
    '        widget=forms.RadioSelect,\n    )',
    '        widget=forms.RadioSelect,\n        required=False,\n    )'
)

# Remove the static fields logic
static_fields_logic = """        if evento_categoria == "FERIA":
            self.fields["cantidad_botes_basura"] = forms.IntegerField(
                label="Botes de basura", min_value=1, initial=1
            )
            self.fields["cantidad_extintores"] = forms.IntegerField(
                label="Extintores", min_value=1, initial=1
            )
            self.fields["modelo_botes_basura"] = forms.CharField(
                label="Nombre o modelo del bote", max_length=150
            )
            self.fields["modelo_extintores"] = forms.CharField(
                label="Nombre o modelo del extintor", max_length=150
            )
            self.fields["foto_botes_basura"] = forms.FileField(
                label="Foto del bote de basura",
                required=not bool(solicitud and solicitud.foto_botes_basura),
                validators=[validate_equipment_image],
                widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"}),
                help_text="JPG, PNG o WEBP (máx. 5 MB).",
            )
            self.fields["foto_extintores"] = forms.FileField(
                label="Foto del extintor",
                required=not bool(solicitud and solicitud.foto_extintores),
                validators=[validate_equipment_image],
                widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"}),
                help_text="JPG, PNG o WEBP (máx. 5 MB).",
            )
            if solicitud:
                self.initial.update({
                    "cantidad_botes_basura": solicitud.cantidad_botes_basura or 1,
                    "cantidad_extintores": solicitud.cantidad_extintores or 1,
                    "modelo_botes_basura": solicitud.modelo_botes_basura,
                    "modelo_extintores": solicitud.modelo_extintores,
                })"""

dynamic_fields_logic = """        from apps.landingpage.models import Evento
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
                
                self.equipos_dinamicos.append({
                    "slug": eq_slug, 
                    "nombre": eq_nombre, 
                    "pedir_foto": eq.get("pedir_foto", False)
                })
                
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
                    )"""

content = content.replace(static_fields_logic, dynamic_fields_logic)

# Change in clean method for programa_especial
clean_prog_old = """        if cleaned.get("programa_especial") != "NINGUNO" and not (cleaned.get("folio_programa_social") or "").strip():"""
clean_prog_new = """        prog_esp = cleaned.get("programa_especial")
        if prog_esp and prog_esp != "NINGUNO" and not (cleaned.get("folio_programa_social") or "").strip():"""
content = content.replace(clean_prog_old, clean_prog_new)

with io.open('apps/muestras/forms.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
