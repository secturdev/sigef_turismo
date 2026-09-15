import io

with io.open('apps/muestras/forms.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will replace self.equipos_dinamicos with self.dynamic_equipment_rows that holds the bound fields
old_code = """                self.equipos_dinamicos.append({
                    "slug": eq_slug, 
                    "nombre": eq_nombre, 
                    "pedir_foto": eq.get("pedir_foto", False)
                })
                
                # Fetch existing value if editing"""

new_code = """                
                # Fetch existing value if editing"""

content = content.replace(old_code, new_code)

old_code2 = """                    self.fields[f"eq_pic_{eq_slug}"] = forms.FileField(
                        label=f"Foto de {eq_nombre}",
                        required=not existing_pic,
                        validators=[validate_equipment_image],
                        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"}),
                        help_text="JPG, PNG o WEBP (máx. 5 MB).",
                    )"""

new_code2 = """                    self.fields[f"eq_pic_{eq_slug}"] = forms.FileField(
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
                })"""

content = content.replace(old_code2, new_code2)

with io.open('apps/muestras/forms.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
