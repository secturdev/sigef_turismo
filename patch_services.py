import io

# Patch forms.py to return dynamic equipment data
with io.open('apps/muestras/forms.py', 'r', encoding='utf-8') as f:
    content = f.read()

part_details_old = """    def participation_details(self):
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
        return products, furniture"""

part_details_new = """    def participation_details(self):
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
        return products, furniture, equipos"""

content = content.replace(part_details_old, part_details_new)

with io.open('apps/muestras/forms.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

# Patch services.py
with io.open('apps/muestras/services.py', 'r', encoding='utf-8') as f:
    content_srv = f.read()

# Replace hardcoded stuff in services.py
old_guardar_paso1_signature = """def guardar_paso1(
    solicitud: SolicitudMuestra,
    data: dict,
    *,
    nombre_comercio: str,
    productos: list[dict],
    mobiliario: list[dict],
) -> SolicitudMuestra:"""

new_guardar_paso1_signature = """def guardar_paso1(
    solicitud: SolicitudMuestra,
    data: dict,
    *,
    nombre_comercio: str,
    productos: list[dict],
    mobiliario: list[dict],
    equipos_dinamicos: list[dict] = None,
) -> SolicitudMuestra:"""

content_srv = content_srv.replace(old_guardar_paso1_signature, new_guardar_paso1_signature)
content_srv = content_srv.replace('    if not solicitud.programa_especial:\n        raise ValidationError({"programa_especial": "Selecciona un programa especial."})\n', '')

old_botes = """    solicitud.cantidad_botes_basura = data.get("cantidad_botes_basura") or 0
    solicitud.cantidad_extintores = data.get("cantidad_extintores") or 0
    solicitud.modelo_botes_basura = (data.get("modelo_botes_basura") or "").strip()
    solicitud.modelo_extintores = (data.get("modelo_extintores") or "").strip()
    if data.get("foto_botes_basura"):
        solicitud.foto_botes_basura = data["foto_botes_basura"]
    if data.get("foto_extintores"):
        solicitud.foto_extintores = data["foto_extintores"]"""

content_srv = content_srv.replace(old_botes, "    pass")

imports_old = "from .models import ImagenComercio, MobiliarioSolicitud, ProductoSolicitud, SolicitudMuestra"
imports_new = "from .models import ImagenComercio, MobiliarioSolicitud, ProductoSolicitud, SolicitudMuestra, EquipamientoAdicionalSolicitud"
content_srv = content_srv.replace(imports_old, imports_new)

old_end = """    for row in mobiliario:
        defaults = {"cantidad": row["quantity"]}
        if row.get("invoice"):
            defaults["factura"] = row["invoice"]
        MobiliarioSolicitud.objects.update_or_create(
            solicitud=solicitud, mobiliario=row["item"], defaults=defaults
        )
    return solicitud"""

new_end = """    for row in mobiliario:
        defaults = {"cantidad": row["quantity"]}
        if row.get("invoice"):
            defaults["factura"] = row["invoice"]
        MobiliarioSolicitud.objects.update_or_create(
            solicitud=solicitud, mobiliario=row["item"], defaults=defaults
        )
    
    if equipos_dinamicos is not None:
        nombres_equipos = [eq["nombre_equipo"] for eq in equipos_dinamicos]
        solicitud.detalle_equipamiento_adicional.exclude(nombre_equipo__in=nombres_equipos).delete()
        for eq in equipos_dinamicos:
            defaults = {"cantidad": eq["cantidad"], "modelo": eq["modelo"]}
            if eq.get("foto"):
                defaults["foto"] = eq["foto"]
            EquipamientoAdicionalSolicitud.objects.update_or_create(
                solicitud=solicitud, nombre_equipo=eq["nombre_equipo"], defaults=defaults
            )
            
    return solicitud"""
content_srv = content_srv.replace(old_end, new_end)

with io.open('apps/muestras/services.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content_srv)

# Patch views.py
with io.open('apps/muestras/views.py', 'r', encoding='utf-8') as f:
    content_views = f.read()

view_call_old = """            productos, mobiliario = form.participation_details()
            guardar_paso1(
                self.solicitud,
                form.cleaned_data,
                nombre_comercio=comercio.nombre,
                productos=productos,
                mobiliario=mobiliario,
            )"""

view_call_new = """            productos, mobiliario, equipos = form.participation_details()
            guardar_paso1(
                self.solicitud,
                form.cleaned_data,
                nombre_comercio=comercio.nombre,
                productos=productos,
                mobiliario=mobiliario,
                equipos_dinamicos=equipos,
            )"""

content_views = content_views.replace(view_call_old, view_call_new)
with io.open('apps/muestras/views.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content_views)

