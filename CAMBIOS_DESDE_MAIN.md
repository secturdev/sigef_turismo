# Cambios realizados desde la rama `main`

## 1. Alcance del informe

Este documento describe las diferencias detectadas entre la rama `main` y el estado actual de la rama `develop`, incluyendo cambios confirmados en Git y modificaciones locales todavía pendientes de commit.

La comparación fue realizada el 1 de septiembre de 2026.

### Resumen técnico

- Rama actual: `develop`.
- Rama de referencia: `main`.
- Commits adicionales en `develop`: 3.
- Archivos comparados contra `main`: 20 archivos versionados, además de migraciones locales todavía no agregadas a Git.
- Magnitud aproximada: más de 2,000 líneas agregadas y 50 líneas eliminadas.

Commits encontrados después de `main`:

1. `10885ca` — Nuevos cambios en `develop`.
2. `52eae24` — Cambios adicionales.
3. `81ba03d` — Inicio de sesión, obtención de datos con Llave Tabasco y llenado automático.

## 2. Integración con Llave Tabasco

Se amplió el backend OIDC para aprovechar los atributos de identidad entregados por Llave Tabasco.

### Sincronización de identidad

Al iniciar sesión se sincronizan con el expediente:

- Nombre o nombres.
- Apellido paterno.
- Apellido materno.
- CURP.
- Correo electrónico.
- Tipo de persona.

El tipo recibido como `Persona física` o `Persona moral` se convierte al valor interno correspondiente del expediente.

### Combinación de atributos OIDC

Se detectó que algunos atributos personalizados, principalmente CURP, tipo de persona y apellido materno, pueden estar presentes en el ID token pero no en la respuesta de `userinfo`.

El backend ahora combina ambas fuentes:

- Los atributos del ID token se conservan.
- Los valores de `userinfo` tienen prioridad cuando el mismo atributo aparece en ambos lugares.

### Protección de datos verificados

Los campos de identidad proporcionados por Llave Tabasco se presentan deshabilitados y no aceptan modificaciones enviadas manualmente desde el navegador:

- Nombre.
- Apellidos.
- CURP.
- Correo electrónico.
- Tipo de persona.

También se agregó un estilo visual diferenciado para controles bloqueados.

## 3. Reestructuración de “Mi perfil”

El acceso anterior de “Mi expediente” fue transformado en una vista unificada denominada “Mi perfil”.

La navegación se realiza mediante pestañas dentro de una sola pantalla:

- Información.
- Comercio.
- Documentos.
- Productos.
- Electrodomésticos, actualmente visible como sección prevista.
- Mobiliario.

Las rutas anteriores del expediente se conservaron para compatibilidad, mientras que el menú lateral y los accesos principales apuntan a la vista unificada.

### Datos generales

Los datos generales ahora se distribuyen en una cuadrícula responsiva:

- Una columna en teléfonos.
- Dos columnas en tabletas.
- Distribución de varias columnas en escritorio.

## 4. Gestión de documentos digitales

Se actualizaron los documentos solicitados según el tipo de persona.

### Persona física

- INE.
- CURP.
- Comprobante de domicilio.
- Constancia de situación fiscal, opcional.

El número de celular y el correo electrónico permanecen como datos estructurados del perfil y no como archivos PDF.

### Persona moral

- INE del representante.
- CURP del representante legal.
- Comprobante de domicilio de la empresa.
- Acta constitutiva de la empresa.
- Poder notarial de la empresa.
- Constancia de situación fiscal de la empresa.

### Documentos obligatorios y opcionales

Se incorporó el campo `obligatorio` al catálogo `TipoDocumento`.

- Los documentos obligatorios participan en el cálculo de avance.
- Los documentos opcionales se muestran en la interfaz, pero no impiden completar el expediente.
- La constancia de situación fiscal de persona física se configuró como opcional.

### Nueva interfaz documental

La presentación inicial fue conservada dentro de un comentario de plantilla y se creó una propuesta nueva basada en un checklist:

- Indicador de documento cargado o pendiente.
- Etiqueta para documentos opcionales.
- Acceso al archivo actual.
- Formulario desplegable para cargar o reemplazar el PDF.
- Apertura automática del formulario cuando existen errores.
- Adaptación para dispositivos móviles.

## 5. Catálogo global de productos

Se agregó el modelo `Producto`, relacionado con el expediente del usuario.

Cada producto permite registrar:

- Nombre.
- Imagen obligatoria.
- Descripción.
- Factura PDF opcional.
- Indicador de producto principal.

### Reglas del catálogo

- Solo puede existir un producto principal por expediente.
- Al elegir un producto principal nuevo, el anterior se desmarca automáticamente.
- Los productos pueden registrarse, editarse y eliminarse.
- Al eliminar un producto también se eliminan su imagen y factura del almacenamiento.
- Las consultas y modificaciones verifican que el producto pertenezca al usuario autenticado.

### Archivos permitidos

- Imágenes: JPG, JPEG, PNG o WEBP, con máximo de 5 MB.
- Facturas: PDF, con máximo de 10 MB.

## 6. Catálogo global de mobiliario

Se agregó el modelo `Mobiliario`, relacionado con el expediente.

Cada registro incluye:

- Nombre.
- Descripción.
- Imagen obligatoria.
- Factura PDF opcional.

El usuario puede registrar, editar y eliminar mobiliario. La eliminación también retira los archivos asociados del almacenamiento privado.

## 7. Información del comercio

Se agregó el modelo `Comercio` con una relación uno a uno respecto del expediente.

La pestaña Comercio permite registrar y actualizar:

- Nombre del comercio.
- Logo del comercio.

El logo acepta JPG, JPEG, PNG o WEBP, con un tamaño máximo de 5 MB.

Cuando el comercio ya está registrado, la interfaz muestra una vista previa con:

- Logo ampliado.
- Nombre del comercio.
- Fondo blanco y borde neutro acorde al resto del perfil.

El nombre puede actualizarse sin volver a cargar el logo.

## 8. Seguridad y almacenamiento de archivos

Las imágenes, facturas y documentos se guardan mediante el almacenamiento privado del expediente.

Se agregaron vistas protegidas para consultar:

- Imágenes de productos.
- Facturas de productos.
- Imágenes de mobiliario.
- Facturas de mobiliario.
- Logo del comercio.
- Versiones de documentos del expediente.

Cada vista valida que el recurso solicitado pertenezca al usuario autenticado.

## 9. Migraciones de base de datos

Se agregaron las siguientes migraciones:

| Migración | Descripción |
| --- | --- |
| `0003_tipodocumento_obligatorio` | Agrega la obligatoriedad al catálogo documental y configura los documentos requeridos. |
| `0004_producto` | Crea el catálogo de productos y la restricción de un producto principal por expediente. |
| `0005_mobiliario` | Crea el catálogo de mobiliario. |
| `0006_comercio` | Crea la información global del comercio. |

Las migraciones `0004_producto.py`, `0005_mobiliario.py` y `0006_comercio.py` todavía aparecen como archivos locales sin seguimiento en Git al momento de elaborar este informe.

Para aplicar los cambios de base de datos:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

## 10. Rutas incorporadas

Se agregaron rutas para:

- Vista unificada de Mi perfil.
- Visualización protegida de imágenes de productos.
- Descarga protegida de facturas de productos.
- Visualización y descarga de archivos de mobiliario.
- Visualización protegida del logo del comercio.

## 11. Interfaz y estilos

Se incorporó `static/src/app-overrides.css`, cargado después del CSS compilado principal.

Esta hoja contiene estilos para:

- Campos deshabilitados.
- Navegación por pestañas.
- Vista documental tipo checklist.
- Formularios y tarjetas de productos.
- Formularios y tarjetas de mobiliario.
- Presentación de la información del comercio.
- Diseño responsivo.

## 12. Pruebas automatizadas

Se ampliaron las pruebas para cubrir:

- Sincronización de atributos OIDC.
- Combinación de ID token y `userinfo`.
- Bloqueo de campos de identidad.
- Tipo de persona administrado por Llave Tabasco.
- Renderizado de Mi perfil.
- Documentos obligatorios y opcionales.
- Registro de productos sin factura.
- Regla de producto principal único.
- Edición y eliminación de productos.
- Eliminación física de archivos de productos.
- Registro, edición y eliminación de mobiliario.
- Registro y actualización del comercio sin reemplazar obligatoriamente el logo.

La última ejecución registró 21 pruebas del módulo de expediente aprobadas.

## 13. Archivos eliminados o pendientes de revisión

La comparación con `main` muestra:

- `.env.example` eliminado respecto de `main`.
- `INFORME_FUNCIONALIDADES_DESARROLLADAS.md` eliminado localmente.

Estas eliminaciones deben revisarse antes de preparar el commit o la integración final para confirmar si son intencionales.

## 14. Recomendaciones antes de integrar

1. Agregar a Git las migraciones `0004`, `0005` y `0006`.
2. Revisar las eliminaciones de `.env.example` y del informe anterior.
3. Ejecutar todas las migraciones en un entorno de prueba.
4. Ejecutar la suite completa de pruebas del proyecto.
5. Probar el inicio de sesión contra el ambiente real de Llave Tabasco.
6. Validar carga, visualización y eliminación de archivos con almacenamiento persistente.
7. Confirmar el alcance funcional de la pestaña Electrodomésticos, que actualmente aparece en la navegación pero todavía no cuenta con catálogo implementado.
