import io

with io.open('apps/muestras/templates/muestras/paso1.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = """        {% if evento_info.categoria == "FERIA" %}
          <fieldset class="event-requirements application-subsection">
            <legend><span>02</span> Equipamiento obligatorio</legend>
            <p>Registra al menos un bote de basura y un extintor. Indica su nombre o modelo y agrega una foto clara.</p>
            <div class="event-requirements__grid">
              <div class="requirement-card">
                <div class="requirement-card__icon" aria-hidden="true">♻</div>
                {% include "components/_form_field.html" with field=form.cantidad_botes_basura %}
                {% include "components/_form_field.html" with field=form.modelo_botes_basura %}
                {% include "components/_form_field.html" with field=form.foto_botes_basura %}
                {% if solicitud.foto_botes_basura %}<a class="requirement-card__current" href="{{ solicitud.foto_botes_basura.url }}" target="_blank" rel="noopener">Ver foto registrada</a>{% endif %}
                <span>Obligatorio: mínimo 1</span>
              </div>
              <div class="requirement-card">
                <div class="requirement-card__icon" aria-hidden="true">🧯</div>
                {% include "components/_form_field.html" with field=form.cantidad_extintores %}
                {% include "components/_form_field.html" with field=form.modelo_extintores %}
                {% include "components/_form_field.html" with field=form.foto_extintores %}
                {% if solicitud.foto_extintores %}<a class="requirement-card__current" href="{{ solicitud.foto_extintores.url }}" target="_blank" rel="noopener">Ver foto registrada</a>{% endif %}
                <span>Obligatorio: mínimo 1</span>
              </div>
            </div>
          </fieldset>
        {% endif %}"""

new_html = """        {% if form.equipos_dinamicos %}
          <fieldset class="event-requirements application-subsection">
            <legend><span>02</span> Equipamiento obligatorio</legend>
            <p>Registra el equipamiento requerido por el evento. Indica su cantidad, modelo y agrega una foto si se solicita.</p>
            <div class="event-requirements__grid">
              {% for eq in form.equipos_dinamicos %}
              <div class="requirement-card">
                <div class="requirement-card__icon" aria-hidden="true">⚙️</div>
                {% include "components/_form_field.html" with field=eq.qty_field %}
                {% include "components/_form_field.html" with field=eq.mod_field %}
                {% if eq.pic_field %}
                    {% include "components/_form_field.html" with field=eq.pic_field %}
                    {% if eq.existing_pic_url %}
                        <a class="requirement-card__current" href="{{ eq.existing_pic_url }}" target="_blank" rel="noopener">Ver foto registrada</a>
                    {% endif %}
                {% endif %}
                <span>Obligatorio: mínimo 1</span>
              </div>
              {% endfor %}
            </div>
          </fieldset>
        {% endif %}"""

content = content.replace(old_html, new_html)

with io.open('apps/muestras/templates/muestras/paso1.html', 'w', encoding='utf-8', newline='') as f:
    f.write(content)
