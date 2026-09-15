import io

with io.open('apps/autenticacion/templates/autenticacion/event_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add step 6 to the steps array
old_steps = """      steps: [
        { number: 1, label: 'Datos básicos' },
        { number: 2, label: 'Boletab' },
        { number: 3, label: 'Catálogo' },
        { number: 4, label: 'Folios' },
        { number: 5, label: 'Documentos' }
      ],"""

new_steps = """      steps: [
        { number: 1, label: 'Datos básicos' },
        { number: 2, label: 'Boletab' },
        { number: 3, label: 'Catálogo' },
        { number: 4, label: 'Folios' },
        { number: 5, label: 'Documentos' },
        { number: 6, label: 'Equipamiento' }
      ],"""

content = content.replace(old_steps, new_steps)

# Add Step 6 section before the form actions
step5_end = """      {% for error in form.documentos_adicionales.errors %}<p class="form-error">{{ error }}</p>{% endfor %}
    </section>"""

step6_section = """      {% for error in form.documentos_adicionales.errors %}<p class="form-error">{{ error }}</p>{% endfor %}
    </section>
    
    <section class="event-config-card event-config-card--step {% if form.equipamiento_obligatorio.errors %}has-error{% endif %}"
      data-step="6" x-show="step === 6" x-cloak x-data="eventEquipmentRequirements()"
      x-init="init($refs.equipmentInput)" x-effect="$refs.equipmentInput.value = JSON.stringify(equipment)">
      {{ form.equipamiento_obligatorio }}
      <header class="event-config-card__header">
        <span>06</span>
        <div><h2>Equipamiento obligatorio</h2><p>Define el equipo obligatorio que los expositores deben registrar para participar.</p></div>
      </header>
      
      <div class="catalog-heading">
        <div>
          <span class="form-label">Equipos requeridos</span>
          <p class="form-help">Añade equipos como sillas, mesas, botes de basura o extintores.</p>
        </div>
        <button type="button" class="btn-outline" @click="addEquipment()">Agregar equipo</button>
      </div>
      <div class="catalog-list event-document-list">
        <template x-for="(eq, index) in equipment" :key="index">
          <article class="catalog-card">
            <div class="catalog-card__head">
              <h3 x-text="`Equipo ${index + 1}`"></h3>
              <button type="button" class="catalog-remove" @click="equipment.splice(index, 1)">Eliminar</button>
            </div>
            <div class="event-document-grid">
              <label class="catalog-field">
                <span class="form-label">Nombre del equipo</span>
                <input class="form-input" x-model.trim="eq.nombre" maxlength="150"
                  placeholder="Ej. Botes de basura" required />
              </label>
            </div>
            <div class="event-document-options">
              <label class="form-check-label"><input class="form-checkbox" type="checkbox"
                x-model="eq.pedir_foto" /> Pedir foto obligatoria</label>
            </div>
          </article>
        </template>
        <div class="catalog-empty" x-show="!equipment.length">
          <strong>Sin equipamiento obligatorio</strong>
          <p>No se solicitará ningún equipo adicional.</p>
        </div>
      </div>
      {% for error in form.equipamiento_obligatorio.errors %}<p class="form-error">{{ error }}</p>{% endfor %}
    </section>"""

content = content.replace(step5_end, step6_section)

alpine_component = """
    Alpine.data('eventEquipmentRequirements', () => ({
      equipment: [],
      init(inputElement) {
        if (inputElement.value) {
          try {
            this.equipment = JSON.parse(inputElement.value);
          } catch (e) {
            this.equipment = [];
          }
        }
      },
      addEquipment() {
        this.equipment.push({
          nombre: '',
          pedir_foto: false
        });
      }
    }));
  });
</script>"""

content = content.replace("  });\n</script>", alpine_component)

with io.open('apps/autenticacion/templates/autenticacion/event_form.html', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
