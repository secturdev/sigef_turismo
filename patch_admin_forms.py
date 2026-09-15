import io
import json

with io.open('apps/autenticacion/forms.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add equipamiento_obligatorio to EventCreateForm fields
old_fields = """    documentos_adicionales = forms.CharField(required=False, widget=forms.HiddenInput)"""
new_fields = """    documentos_adicionales = forms.CharField(required=False, widget=forms.HiddenInput)
    equipamiento_obligatorio = forms.CharField(required=False, widget=forms.HiddenInput)"""
content = content.replace(old_fields, new_fields)

old_meta = """            "boletab_eventos",
            "catalogo_giros",
            "catalogo_folios",
            "documentos_adicionales","""
new_meta = """            "boletab_eventos",
            "catalogo_giros",
            "catalogo_folios",
            "documentos_adicionales",
            "equipamiento_obligatorio","""
content = content.replace(old_meta, new_meta)

old_init = """            self.initial["documentos_adicionales"] = json.dumps(
                self.instance.documentos_adicionales, ensure_ascii=False
            )"""
new_init = """            self.initial["documentos_adicionales"] = json.dumps(
                self.instance.documentos_adicionales, ensure_ascii=False
            )
            self.initial["equipamiento_obligatorio"] = json.dumps(
                self.instance.equipamiento_obligatorio, ensure_ascii=False
            )"""
content = content.replace(old_init, new_init)

old_init2 = """        self.fields["documentos_adicionales"].widget.attrs["x-ref"] = "requirementsInput" """
new_init2 = """        self.fields["documentos_adicionales"].widget.attrs["x-ref"] = "requirementsInput"
        self.fields["equipamiento_obligatorio"].widget.attrs["x-ref"] = "equipmentInput" """
content = content.replace(old_init2, new_init2)

old_save = """        event.documentos_adicionales = self.cleaned_data["documentos_adicionales"]"""
new_save = """        event.documentos_adicionales = self.cleaned_data["documentos_adicionales"]
        event.equipamiento_obligatorio = self.cleaned_data.get("equipamiento_obligatorio", [])"""
content = content.replace(old_save, new_save)

clean_equipamiento = """
    def clean_equipamiento_obligatorio(self):
        raw = self.cleaned_data.get("equipamiento_obligatorio") or "[]"
        try:
            equipment = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            raise forms.ValidationError("La configuración de equipamiento no es válida.")
        if not isinstance(equipment, list):
            raise forms.ValidationError("La configuración de equipamiento no es válida.")
        
        cleaned = []
        for index, item in enumerate(equipment, start=1):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"El equipo {index} no es válido.")
            nombre = str(item.get("nombre") or "").strip()
            if not nombre:
                raise forms.ValidationError(f"Escribe el nombre del equipo {index}.")
            cleaned.append({
                "nombre": nombre,
                "pedir_foto": bool(item.get("pedir_foto", False))
            })
        return cleaned
"""

content = content.replace('    def clean_catalogo_folios(self):', clean_equipamiento + '\n    def clean_catalogo_folios(self):')

with io.open('apps/autenticacion/forms.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
