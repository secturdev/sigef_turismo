import io
with io.open('apps/muestras/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '            and self.programa_especial\n            and (self.programa_especial == "NINGUNO" or self.folio_programa_social)',
    '            and (not self.programa_especial or self.programa_especial == "NINGUNO" or self.folio_programa_social)'
)

content += '''

class EquipamientoAdicionalSolicitud(models.Model):
    solicitud = models.ForeignKey(
        SolicitudMuestra, on_delete=models.CASCADE, related_name='detalle_equipamiento_adicional'
    )
    nombre_equipo = models.CharField('nombre de equipo', max_length=150)
    cantidad = models.PositiveIntegerField('cantidad', default=1)
    modelo = models.CharField('modelo', max_length=150, blank=True)
    foto = models.FileField(
        'foto', upload_to=_ruta_foto_equipamiento, blank=True
    )

    class Meta:
        verbose_name = 'equipamiento adicional'
        verbose_name_plural = 'equipamientos adicionales'
'''

with io.open('apps/muestras/models.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
