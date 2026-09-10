# Cambios de administración e integración con Boletab

## Alcance

Este documento resume los cambios realizados en SIGEF desde la creación del acceso administrativo hasta la consulta y configuración visual de espacios obtenidos desde Boletab.

No se incluyen secretos, contraseñas ni valores de API keys. El endpoint de espacios disponibles para sistemas externos fue analizado, pero todavía no ha sido implementado.

## 1. Acceso administrativo

Se agregó un inicio de sesión independiente para administradores mediante correo electrónico y contraseña.

Ruta:

```text
/administracion/login/
```

El acceso valida que la cuenta:

- Exista y tenga una contraseña válida.
- Esté activa.
- Tenga el atributo `is_staff=True`.

Los usuarios normales no pueden iniciar sesión desde esta pantalla. Al autenticarse correctamente, el administrador es enviado al panel administrativo.

También se configuró una cuenta administrativa inicial. Su contraseña no se documenta en el repositorio.

## 2. Panel y navegación administrativa

Se creó un layout administrativo basado en la estructura visual utilizada por el expositor.

Incluye:

- Sidebar adaptable a dispositivos móviles.
- Logo institucional de SIGEF.
- Navegación para inicio, administradores y eventos.
- Correo de la cuenta autenticada.
- Identificación del rol como `Administrador` o `Superadministrador`.
- Cierre de sesión independiente que regresa al login administrativo.

Rutas principales:

```text
/administracion/
/administracion/logout/
```

## 3. Alta de usuarios administradores

Se agregó una pantalla para registrar cuentas con acceso administrativo.

Ruta:

```text
/administracion/usuarios/
```

El formulario solicita:

- Nombre.
- Correo electrónico.
- Contraseña.
- Confirmación de contraseña.

Las contraseñas se guardan utilizando el sistema de hash de Django. También se aplican los validadores de seguridad configurados por el proyecto.

Las cuentas creadas desde esta vista quedan activas y con `is_staff=True`, pero no reciben automáticamente privilegios de superusuario.

## 4. Administración de eventos SIGEF

Se creó el modelo `Evento` dentro de `apps.landingpage`.

Campos principales:

- `nombre`.
- `descripcion`.
- `imagen`.
- `visible`.
- `boletab_eventos`, que conserva las relaciones con uno o varios eventos externos.
- `fecha_registro`.

La administración se separó en diferentes vistas:

```text
/administracion/eventos/                  Listado
/administracion/eventos/nuevo/            Creación
/administracion/eventos/<id>/editar/      Actualización
```

El listado muestra la imagen, nombre, descripción, visibilidad y eventos relacionados de Boletab.

Los eventos marcados como visibles se incorporan a las tarjetas mostradas en la página pública y en la vista de eventos de los expositores.

## 5. Configuración de Boletab

La conexión utiliza las siguientes variables de entorno:

```text
BOLETAB_BASE_URL
BOLETAB_API_KEY
BOLETAB_TIMEOUT
```

La clave se envía exclusivamente mediante el header:

```http
X-API-KEY: <clave configurada>
```

Las solicitudes se realizan desde el servidor SIGEF. No se envía un header `Origin` y la API key nunca se entrega al navegador.

El cliente reconoce errores de:

- Configuración incompleta.
- API key o IP no autorizada.
- Respuestas HTTP inesperadas.
- DNS, conexión o timeout.
- JSON o estructura de respuesta no reconocida.

## 6. Catálogo de eventos de Boletab

Para llenar el selector de eventos externos se consulta:

```http
GET {BOLETAB_BASE_URL}/eventos
```

El formulario de SIGEF utiliza un `<select multiple>`, por lo que un evento local puede relacionarse con varios eventos de Boletab.

Por cada evento seleccionado se conserva al menos:

```json
{
  "id": "61",
  "name": "Nombre del evento en Boletab"
}
```

Al editar un evento se restauran todas las selecciones guardadas. Si Boletab no está disponible durante una edición, las relaciones actuales se mantienen como opciones para evitar perderlas.

## 7. Consulta de lugares y mapa SVG

La pantalla de espacios se habilita solamente cuando el evento SIGEF tiene al menos un evento de Boletab relacionado.

Ruta:

```text
/administracion/eventos/<id>/espacios/
```

La consulta de lugares utiliza:

```http
GET {BOLETAB_BASE_URL}/eventos/{eventoId}/lugares?page=0&size=1000
```

La respuesta real de Boletab es paginada y entrega los registros dentro de `content`. SIGEF utiliza `totalPages` para consultar todas las páginas cuando sea necesario.

Durante la validación se consultó el evento Boletab con ID `61` y se procesaron 56 lugares.

### Representación visual

Cada lugar se dibuja como un polígono SVG usando `pathSvg`. Otros campos utilizados son:

- `asientoId` como identificador estable del espacio.
- `posX` y `posY` para ubicar la etiqueta.
- `etiqueta` como texto visible.
- `categoriaColor` como color base.
- `habilitado` y `estado` para representar disponibilidad.
- `seccionNombre`, `seccionTipo`, `fila`, `numero`, `categoriaNombre` y `precio` para la ficha informativa.

Las etiquetas calculan automáticamente el tamaño disponible. Cuando es necesario se dividen en dos líneas, reducen la tipografía y se recortan dentro del polígono para evitar desbordamientos.

### Navegación del mapa

El mapa permite:

- Acercar y alejar mediante botones.
- Hacer zoom con la rueda del mouse sobre la posición del cursor.
- Arrastrar horizontal y verticalmente.
- Utilizar gestos de puntero en pantallas táctiles.
- Restablecer la vista inicial.
- Seleccionar un stand sin confundir la selección con el desplazamiento.

## 8. Información y reglas por espacio

Al seleccionar un espacio se muestra directamente en el panel derecho:

- Etiqueta.
- Sección y tipo.
- Fila y número.
- Categoría.
- Estado.
- Precio.
- ID del asiento en Boletab.

La configuración de reglas se realiza en el mismo panel, sin abrir otro sidebar o modal.

El modelo `ReglaEspacio` identifica cada configuración mediante:

- Evento SIGEF.
- ID del evento Boletab.
- `asientoId` de Boletab.

La combinación de esos tres valores es única.

### Constructor de reglas

El administrador puede presionar `Agregar regla` y configurar una pareja:

```text
Giro -> Subgiro
```

El selector de subgiro se filtra según el giro elegido. Al cambiar de giro se elimina cualquier subgiro incompatible.

Es posible:

- Agregar varias parejas giro-subgiro.
- Eliminar reglas individuales.
- Capturar varios folios, uno por línea.
- Dejar las reglas vacías para no restringir el espacio.

El servidor vuelve a validar que cada subgiro pertenezca realmente al giro recibido y normaliza los folios en mayúsculas sin duplicados.

La estructura principal almacenada para las reglas es similar a:

```json
[
  {
    "giro": "ARTESANIAS",
    "subgiro": "TEXTILES"
  },
  {
    "giro": "TURISMO_EXPERIENCIAS",
    "subgiro": "TOURS"
  }
]
```

## 9. Endpoint futuro de espacios disponibles

Se definió conceptualmente que un sistema externo podrá solicitar los espacios disponibles para un usuario y un evento.

SIGEF deberá resolver internamente:

1. La identidad del usuario.
2. Su participación en el evento.
3. Su giro, subgiro y folio.
4. Las reglas de cada espacio.
5. La disponibilidad actual reportada por Boletab.

La respuesta deberá incluir solamente los espacios que el usuario puede visualizar o seleccionar, sin exponer CURP, giro, subgiro, folio ni otros datos personales.

Este endpoint todavía no forma parte de los cambios implementados.

## 10. Migraciones

Se agregaron migraciones para:

- Crear el modelo de eventos.
- Incorporar la relación con eventos Boletab.
- Convertir la relación individual inicial al formato múltiple.
- Crear las reglas por espacio.
- Incorporar las parejas estructuradas de giro y subgiro.

Las migraciones se encuentran en:

```text
apps/landingpage/migrations/
```

## 11. Verificación

Se agregaron pruebas para cubrir, entre otros escenarios:

- Login administrativo correcto.
- Rechazo de usuarios sin permisos.
- Alta de administradores.
- Creación y actualización de eventos.
- Restricción de acceso a vistas administrativas.
- Habilitación de la configuración de espacios.
- Renderizado de polígonos.
- Persistencia y validación de reglas.
- Conservación de las relaciones con Boletab.

La última ejecución completa reportó 44 pruebas aprobadas y ninguna incidencia en `manage.py check`.
