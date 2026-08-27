# Informe de funcionalidades desarrolladas

## Sistema SIGEF Turismo

**Fecha de corte:** 27 de agosto de 2026  
**Base del informe:** revisión funcional y técnica del código fuente disponible en el repositorio.

---

## 1. Resumen ejecutivo

SIGEF Turismo cuenta actualmente con una plataforma web orientada a personas y prestadores interesados en integrar un expediente digital y participar en convocatorias o eventos de la Secretaría de Turismo.

El desarrollo disponible cubre cuatro componentes principales:

1. Un portal público para presentar eventos y convocatorias.
2. Registro, inicio y cierre de sesión de usuarios, incluida la preparación para autenticación mediante Llave Tabasco.
3. Un expediente digital reutilizable con datos generales, documentos, control de vigencia y avance.
4. Un flujo de registro al Festival del Chocolate para capturar información e imágenes de un comercio.

El sistema tiene persistencia en PostgreSQL, interfaz adaptable, controles de seguridad, almacenamiento privado de documentos y pruebas automatizadas de las principales reglas del expediente y autenticación.

---

## 2. Alcance funcional desarrollado

### 2.1 Portal público

La página de inicio ofrece:

- Presentación visual institucional del sistema.
- Carrusel de eventos destacados.
- Difusión de Feria Tabasco 2027 y Festival del Chocolate Tabasco 2026.
- Catálogo visual de eventos construido a partir de los recursos gráficos disponibles.
- Acceso a registro e inicio de sesión.
- Acceso a la convocatoria habilitada del Festival del Chocolate.
- Navegación y pie de página con identidad gráfica institucional.
- Diseño adaptable para distintos tamaños de pantalla.

Actualmente aparecen en el catálogo:

- Festival del Chocolate.
- Expo Navideña.
- Feria Tabasco.
- Motonáutica.

De estos eventos, únicamente el Festival del Chocolate tiene habilitado un flujo de registro. Los demás funcionan por ahora como elementos informativos sin enlace funcional de inscripción o detalle.

### 2.2 Gestión de usuarios y acceso

El sistema permite:

- Crear una cuenta usando correo electrónico.
- Capturar un nombre visible opcional.
- Definir y confirmar una contraseña.
- Validar que ambas contraseñas coincidan.
- Aplicar la política de contraseñas de Django, incluyendo una longitud mínima de 12 caracteres.
- Iniciar sesión mediante correo y contraseña.
- Cerrar sesión.
- Redirigir al tablero después del registro o inicio de sesión.
- Evitar que un usuario autenticado vuelva a las pantallas de registro o acceso.
- Crear automáticamente un expediente al registrar una cuenta.

El modelo de usuario es propio del sistema y utiliza el correo electrónico como identificador único.

### 2.3 Integración con Llave Tabasco

El proyecto incorpora la base técnica para autenticación federada mediante OpenID Connect (OIDC):

- Ruta de acceso mediante Llave Tabasco.
- Configuración de emisor, cliente, secreto y endpoints OIDC por variables de entorno.
- Recepción y validación de identidad mediante tokens firmados con RS256.
- Asociación del identificador externo `sub` con el usuario local.
- Creación o actualización del usuario local a partir de la identidad externa.
- Creación automática del expediente para usuarios autenticados por OIDC.
- Cierre de sesión coordinado con el proveedor de identidad cuando existe un token válido.
- Posibilidad de activar o desactivar la integración por configuración.

Su funcionamiento completo depende de contar con credenciales y endpoints válidos del proveedor Llave Tabasco.

### 2.4 Tablero del usuario

Después de autenticarse, el usuario dispone de un tablero privado que:

- Recupera o crea su expediente único.
- Muestra el porcentaje de avance del expediente.
- Indica cuántos componentes requeridos están completos.
- Identifica el siguiente paso pendiente.
- Muestra el estado de los documentos requeridos.
- Permite continuar la integración del expediente.
- Incluye navegación hacia expediente y eventos.

El porcentaje se calcula considerando:

- Selección del tipo de persona.
- Captura completa de datos generales.
- Carga de cada documento aplicable al tipo de persona.

### 2.5 Expediente digital único

Cada usuario tiene un solo expediente. El flujo está dividido en tres pasos.

#### Paso 1. Tipo de persona

El usuario puede identificarse como:

- Persona física.
- Persona moral.
- Ciudadano.

La selección determina qué campos y documentos serán requeridos en los pasos posteriores.

#### Paso 2. Datos generales

El sistema adapta el formulario al tipo de persona.

Para persona física o ciudadano contempla:

- Nombres.
- Apellido paterno.
- Apellido materno.
- CURP.
- Número de celular.
- Correo electrónico de contacto.

Para persona moral contempla:

- Razón social.
- CURP del representante legal.
- Nombre del representante legal.

También existe soporte en el modelo y los servicios para:

- RFC.
- Domicilio.
- Campos adicionales configurables.
- Campos adicionales aplicables solo a determinados tipos de persona.
- Campos adicionales obligatorios u opcionales.
- Tipos de dato configurables: texto, número, fecha y sí/no.

El formulario actual no expone RFC ni domicilio y el catálogo inicial desactiva los campos adicionales. Estas capacidades existen en la estructura de datos, pero no forman parte del flujo visible actual.

Validaciones implementadas:

- Formato estructural de CURP.
- Normalización de CURP a mayúsculas.
- Formato estructural de RFC en la capa de validación.
- Teléfono con al menos 10 dígitos y formato permitido.
- Correo electrónico válido.
- Campos obligatorios según el tipo de persona.

#### Paso 3. Documentos

El sistema permite:

- Consultar los documentos aplicables al tipo de persona.
- Cargar documentos únicamente en formato PDF.
- Limitar cada archivo a un máximo de 10 MB.
- Registrar fecha de emisión y fecha de vencimiento.
- Calcular automáticamente el vencimiento cuando el tipo de documento tiene días de vigencia configurados.
- Sustituir la versión vigente sin eliminar versiones anteriores.
- Conservar historial de versiones por documento.
- Registrar nombre original, fecha de carga y hash SHA-256 del archivo.
- Descargar una versión del documento mediante una vista autenticada.
- Impedir que otro usuario descargue documentos ajenos.
- Guardar archivos con nombres aleatorios para evitar colisiones o exposición del nombre original.
- Mantener los documentos fuera del almacenamiento público.

Estados documentales calculados:

- Vigente.
- Por vencer, cuando faltan 30 días o menos.
- Vencido.
- Sin fecha de vencimiento.

Catálogo inicial de documentos por tipo de persona:

| Tipo de persona | Documentos requeridos |
|---|---|
| Ciudadano | INE; comprobante de domicilio |
| Persona física | INE; comprobante de domicilio; constancia de situación fiscal |
| Persona moral | INE del representante; comprobante de domicilio de la empresa; acta constitutiva; poder notarial; constancia de situación fiscal de la empresa |

Vigencias configuradas:

- Comprobantes de domicilio: 90 días.
- Constancias de situación fiscal: 30 días.
- Los demás documentos no tienen vencimiento automático configurado.

### 2.6 Catálogo privado de eventos

Los usuarios autenticados cuentan con una vista de eventos dentro del sistema. Esta reutiliza el catálogo público y permite dirigirse al registro del evento habilitado.

### 2.7 Solicitud para el Festival del Chocolate

Se desarrolló un flujo privado de dos pasos para el registro de un comercio al Festival del Chocolate.

#### Paso 1. Información del comercio

Permite capturar:

- Nombre del comercio.
- Giro.
- Programa especial al que pertenece.

Giros disponibles:

- Chocolate artesanal.
- Cacao y derivados.
- Repostería.
- Bebidas tradicionales.
- Gastronomía tabasqueña.
- Artesanías.
- Turismo y experiencias.
- Moda y diseño.
- Tecnología local.
- Servicios empresariales.

Programas especiales disponibles:

- Origen Tabasco.
- Tandas para la Mujer.
- Código de Barras.

La pantalla también consulta datos del expediente global del usuario para mostrar información ya registrada, evitando volver a capturarla en la solicitud.

#### Paso 2. Material gráfico

Permite:

- Cargar el logo del comercio.
- Cargar una o varias imágenes del comercio.
- Aceptar archivos JPG, JPEG, PNG y WEBP.
- Limitar cada archivo a 5 MB.
- Conservar como máximo cinco imágenes del comercio.
- Mantener archivos previamente cargados al volver al formulario.
- Validar que exista un logo y al menos una imagen antes de finalizar.

#### Finalización

El flujo incluye:

- Validación secuencial: no se accede al segundo paso sin completar el primero.
- Validación final de ambos pasos.
- Pantalla de confirmación de registro completado.
- Persistencia de una solicitud por usuario.
- Seguimiento del paso alcanzado y fechas de creación y actualización.

---

## 3. Reglas de negocio implementadas

- Un correo electrónico solo puede pertenecer a un usuario.
- Cada usuario solo puede tener un expediente.
- Cada usuario solo puede tener una solicitud para el Festival del Chocolate.
- El expediente se crea automáticamente cuando es necesario.
- Los requisitos de datos y documentos cambian según el tipo de persona.
- Solo se contabilizan como requeridos los documentos activos y aplicables.
- Cada expediente conserva un solo registro lógico por tipo de documento.
- Una nueva carga crea una versión y se convierte en la versión actual sin borrar el historial.
- Un usuario únicamente puede descargar documentos pertenecientes a su propio expediente.
- La solicitud del evento debe completarse en orden.
- El logo y al menos una imagen son obligatorios para finalizar la solicitud.
- No se permiten más de cinco imágenes de comercio por solicitud.

---

## 4. Seguridad y protección de información

El desarrollo incorpora:

- Protección CSRF en formularios.
- Autenticación obligatoria en tablero, expediente, eventos privados y solicitudes.
- Contraseñas almacenadas mediante hash; Argon2 está configurado como algoritmo preferente.
- Política de contraseña robusta.
- Bloqueo temporal después de cinco intentos fallidos de acceso mediante Django Axes.
- Sesiones HTTP-only, con cierre al cerrar el navegador y duración configurada de dos horas.
- Política de seguridad de contenido (CSP).
- Protección contra inclusión en marcos mediante `X-Frame-Options: DENY`.
- Prevención de detección incorrecta de tipos de contenido.
- Política de referente restringida al mismo origen.
- CORS limitado a orígenes autorizados por configuración.
- Cookies seguras, redirección HTTPS y HSTS en ambiente productivo.
- Documentos privados servidos solamente después de verificar autenticación y propiedad.
- Cálculo SHA-256 por cada versión documental para apoyar la verificación de integridad.
- Configuración sensible separada en variables de entorno.

---

## 5. Componentes técnicos desarrollados

- Backend: Python y Django 5.2.
- Base de datos: PostgreSQL.
- Renderizado web: plantillas Django.
- Diseño: Tailwind CSS y Flowbite.
- Interacciones de interfaz: JavaScript, Alpine.js y Swiper.
- Autenticación federada: OpenID Connect mediante `mozilla-django-oidc`.
- Archivos estáticos en producción: WhiteNoise.
- Servidor de despliegue: Gunicorn.
- Configuraciones separadas para desarrollo y producción.
- Idioma y zona horaria: español de México y America/Mexico_City.
- Migraciones de base de datos para usuarios, expedientes, documentos y solicitudes.
- Comando de carga inicial del catálogo documental: `seed_expediente`.

El proyecto incluye además Django REST Framework, filtros y tablas como dependencias preparadas para crecimiento; sin embargo, en el código revisado no existen todavía endpoints API, serializadores ni vistas REST funcionales.

---

## 6. Verificación realizada

Se ejecutaron las pruebas automatizadas existentes del proyecto con resultado satisfactorio:

- **12 pruebas ejecutadas.**
- **12 pruebas aprobadas.**
- **0 errores y 0 fallos.**
- La revisión interna de Django no reportó problemas de configuración del sistema.

Las pruebas cubren, entre otros puntos:

- Registro e inicio de sesión por correo.
- Un expediente por usuario.
- Reglas de datos por tipo de persona.
- Validadores de CURP y RFC.
- Campos adicionales.
- Versionado de documentos.
- Detección de documentos vencidos y vigentes.
- Restricción de descarga entre usuarios.
- Descarga por el propietario.
- Cálculo de avance del expediente.

No se encontraron pruebas automatizadas específicas para el portal público, la integración real con Llave Tabasco ni el flujo de solicitud del Festival del Chocolate.

---

## 7. Funcionalidades parciales o preparadas

Las siguientes capacidades están desarrolladas solo de manera parcial o requieren configuración externa:

- **Llave Tabasco:** la integración OIDC está programada, pero requiere credenciales, endpoints y validación contra el ambiente real del proveedor.
- **Otros eventos:** Feria Tabasco, Expo Navideña y Motonáutica se muestran en el catálogo, pero no tienen páginas de detalle ni formularios de inscripción funcionales.
- **Campos adicionales:** existe el modelo dinámico, su almacenamiento y presentación en formulario, aunque la carga inicial actual los desactiva.
- **RFC y domicilio:** existen en el modelo de datos; RFC cuenta con validador, pero ninguno se captura en el formulario visible actual.
- **Resumen del expediente:** existe la ruta, pero actualmente redirige al tablero y no presenta una pantalla de resumen propia.
- **API:** las dependencias y configuración base están incluidas, pero no hay endpoints implementados.

---

## 8. Funcionalidades no identificadas en el desarrollo actual

Durante la revisión no se encontró implementación de:

- Panel administrativo o consola operativa para personal de la Secretaría.
- Gestión de roles distintos de usuario y superusuario técnico.
- Bandeja para revisar, aprobar, rechazar u observar expedientes.
- Revisión, dictaminación o cambio de estado de solicitudes de eventos.
- Envío formal o folio de una solicitud.
- Notificaciones por correo electrónico, SMS o dentro del sistema.
- Recuperación o restablecimiento de contraseña.
- Firma electrónica.
- Generación de constancias, acuses o documentos PDF.
- Reportes, estadísticas o exportación de información.
- Buscador o filtros de expedientes y solicitudes.
- Bitácora funcional de acciones o auditoría administrativa.
- Eliminación o reemplazo controlado de imágenes de una solicitud.
- Inscripciones para eventos distintos del Festival del Chocolate.
- Pruebas automatizadas del módulo de muestras/solicitudes.

Esta sección no implica necesariamente defectos: delimita las capacidades que no forman parte del avance comprobado al corte del informe.

---

## 9. Estado general del avance

El proyecto cuenta con una base funcional para el autoservicio del usuario: registro, autenticación, integración de expediente y carga privada de documentos. Sobre esa base ya existe una primera inscripción especializada para un evento, el Festival del Chocolate.

Para una siguiente etapa, el mayor bloque pendiente es la operación institucional posterior a la captura: recepción formal, folios, revisión, observaciones, aprobación o rechazo, notificaciones y reportes administrativos. También será necesario habilitar los flujos de los demás eventos y ampliar la cobertura de pruebas antes de una liberación productiva.

---

## 10. Conclusión para presentación

SIGEF Turismo ya demuestra el flujo principal del lado ciudadano: una persona puede crear su cuenta, integrar un expediente digital según su perfil, cargar y consultar documentación de forma segura, conocer su avance y registrar información de su comercio para participar en el Festival del Chocolate.

La arquitectura implementada permite reutilizar el expediente en futuras convocatorias y ampliar los catálogos de documentos, campos y eventos. El siguiente paso natural es incorporar las funciones internas de gestión y dictaminación que permitan a la Secretaría administrar de principio a fin la información recibida.
