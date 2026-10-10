# Planeación: Control de Procesos (Juzgado) — app de escritorio Python multiusuario

## Estado

| Fase | Estado | Notas |
|---|---|---|
| 0. Base y prueba de concepto | Hecha | Falta comprobar en Windows la impresión/PDF y el guardado de archivos dentro de WebView2. |
| 1. Dominio y BD | Hecha | Reglas en Python verificadas contra el JS original; 18 tablas, migración inicial y semillas. |
| 2. API | Hecha | 67 endpoints: sesión, usuarios y roles, procesos, actuaciones, tablero, paquetes, configuración, documentos, auditoría. Se exploran en `/api/docs`. |
| 3. Frontend | Hecha | Pantallas originales conectadas a la API, ingreso, usuarios, roles y auditoría. Probado en navegador; falta probar impresión y exportación dentro de la ventana en Windows. |
| 4. Respaldos | Hecha | Exportar y restaurar JSON, formato del HTML original, respaldo automático diario con rotación y respaldo previo a cada restauración. |
| 5. Escritorio y empaquetado | Construida | Asistente Servidor/Cliente probado en la ventana real (Mac). El instalador ya se construye en Windows con `packaging\construir.ps1` (77 pruebas en verde). Falta probar en el despacho la bandeja, la impresión y la conexión entre dos equipos. |
| 6. Verificación final | Pendiente | |

Cómo ver el avance: `uv run pytest` (pruebas) y `uv run control-procesos` (app). Otras opciones: `--sin-ventana` (solo servidor, para entrar por navegador), `--cliente URL`, `--reconfigurar`.

## Contexto

Hoy existe `control_procesos.html`: una SPA de un solo archivo (1036 líneas, JS vanilla) que guarda todo en `localStorage` como un único objeto `DB = {procesos, actuaciones, config, plantillas}`. Es monousuario y los datos viven en un navegador.

`requerimientos.txt` pide llevar esas funcionalidades a un proyecto Python que corra en Windows como app nativa, con SQLite, respaldo/restauración en JSON, usuarios con autenticación y roles por permisos, y acceso de otros equipos en red local con un equipo servidor.

Decisiones ya tomadas con el usuario:
- UI: se reutiliza el HTML/JS actual dentro de una ventana nativa (pywebview), hablando con una API.
- Clientes LAN: el mismo `.exe`, que en el primer arranque se configura como **Servidor** o **Cliente**.
- Permisos: roles editables con catálogo de permisos; un rol por usuario.
- Extras en v1: importar respaldos del HTML actual, auditoría, backups automáticos, instalador.

## Qué hace la app actual (inventario a trasladar)

- **Procesos**: radicado, naturaleza, clase, demandante, demandado, fecha de radicación, situación, macroetapa, notas.
- **Actuaciones** por proceso y cuaderno: materia, tipo de solicitud, origen, descripción, fechas del ciclo (memorial, constancia, pasa/pase, providencia, ejecutoria, cumplida), término (catálogo o personalizado), fecha de inicio, suspende, observaciones, ruta y paso.
- **Reglas derivadas** (no se guardan, se calculan): `codigo()` (10 situaciones), `ubicacion()`, `diasEstado()`, `vencimiento()`/`calcVenc()` con días hábiles, `estTermino()`, `resultado()`, `procDeriv()` (represamiento, inactividad, próximo vencimiento), `globalStats()`.
- **Calendario judicial**: festivos 2026–2030 fijos + suspensiones por rango, días cerrados y días reabiertos (`esHabil()`).
- **Rutas procesales**: secuencias de pasos, mapa tipo de solicitud → ruta, propuesta de "siguiente paso".
- **Vistas**: Tablero (KPIs, próximos vencimientos), Procesos (filtros + búsqueda), Gestión por paquetes (materia/estado/tipo, imprimir lista, CSV), Detalle (cuadernos, línea de tiempo, notas), Configuración (catálogos, términos, rutas, calendario, plantillas y firmantes, apariencia, datos del juzgado).
- **Documentos**: constancia y pase al despacho desde plantillas con `{{campos}}`, membrete y antefirma (imágenes base64), fecha en letras, impresión/PDF.
- **Respaldo**: exportar/importar el `DB` completo en JSON; datos de ejemplo; vaciar todo.

## Arquitectura

```
[.exe modo Servidor]                      [.exe modo Cliente]
 pywebview ──► http://127.0.0.1:8765       pywebview ──► http://IP-servidor:8765
 uvicorn + FastAPI (0.0.0.0:8765)
 SQLite (WAL) en %PROGRAMDATA%\ControlProcesos\
```

- **Stack**: Python 3.12, FastAPI + uvicorn, SQLAlchemy 2 + Alembic, SQLite en modo WAL, argon2 (`argon2-cffi`) para contraseñas, pywebview (WebView2), pystray, APScheduler, pytest, PyInstaller + Inno Setup.
- **Reglas de negocio en Python** como única fuente de verdad. La API devuelve cada actuación/proceso con sus campos derivados; el frontend solo pinta. La vista previa del formulario de actuación (`syncActForm`) usa un endpoint `POST /api/actuaciones/derivar` sobre datos sin guardar.
- **Frontend**: se parte el HTML en `index.html` + `app.css` + módulos JS. Se elimina `localStorage`/`save()`; cada mutación llama a la API y refresca la vista. Se quitan del JS las funciones de cálculo.
- **Servidor**: corre mientras la app está abierta en el equipo servidor; al cerrar la ventana queda en la bandeja del sistema. Opción "iniciar con Windows". (Servicio de Windows queda para después.)
- **Concurrencia**: columna `version` en procesos y actuaciones; si otro usuario editó antes, la API responde 409 y el frontend recarga. Las vistas se refrescan al cambiar de pestaña y cada 30 s.

## Estructura del proyecto

```
juzgado/
  pyproject.toml
  app/
    main.py              # arranque: lee modo, levanta servidor y/o ventana
    desktop/             # pywebview, bandeja, asistente de primer arranque, js_api (guardar archivo)
    server/
      api/               # routers: auth, usuarios, roles, procesos, actuaciones, config, documentos, respaldo, auditoria
      core/              # settings, seguridad, permisos, sesiones
      db/                # models.py, session.py, seeds.py
      domain/            # calendario.py, terminos.py, estados.py, rutas.py, plantillas.py, fechas_letras.py
      services/          # respaldo.py (export/restore/legacy), auditoria.py, scheduler.py
    web/                 # index.html, login.html, css/, js/
  migrations/            # Alembic
  tests/
  packaging/             # juzgado.spec, installer.iss
  legacy/control_procesos.html   # referencia, se mueve aquí
```

## Modelo de datos (SQLite)

- `usuarios` (usuario, nombre, hash, rol_id, activo, preferencias de tema), `roles`, `rol_permisos`, `sesiones`.
- `procesos`, `actuaciones` (mismos campos del HTML + `version`, `creado_por`, `actualizado_por`, marcas de tiempo).
- `catalogos` (tipo, valor, orden) para materias, tipos de solicitud, cuadernos, macroetapas, asuntos civil/familia.
- `terminos`, `rutas`, `ruta_pasos`, `tipo_ruta`.
- `festivos`, `cal_suspensiones`, `cal_dias` (cerrado | reabierto).
- `plantillas`, `firmantes` (imagen como BLOB), `config` (juzgado, ciudad, prefijo, membrete).
- `auditoria` (usuario, fecha, entidad, id, acción, antes/después en JSON).

Las actuaciones guardan cuaderno, materia, tipo y término **como texto**, igual que hoy: así borrar una opción del catálogo no altera lo ya registrado y la importación del respaldo viejo es directa.

Los catálogos por defecto (términos, asuntos, rutas, plantillas, festivos, membrete y antefirma) se extraen del HTML a `seeds.py`.

## Usuarios, autenticación y permisos

- Primer arranque en modo servidor: asistente que crea el usuario administrador.
- Login con usuario y contraseña; sesión con token opaco guardado en BD y cookie HttpOnly, con vencimiento y cierre de sesión.
- Catálogo de permisos definido en código (`core/permisos.py`), agrupado por módulo:
  `procesos.{ver,crear,editar,eliminar,notas}`, `actuaciones.{ver,crear,editar,eliminar}`, `documentos.generar`, `paquetes.{ver,exportar}`, `config.{catalogos,terminos,rutas,calendario,plantillas,juzgado}`, `respaldo.{exportar,restaurar,vaciar}`, `usuarios.gestionar`, `roles.gestionar`, `auditoria.ver`.
- Cada endpoint declara su permiso con una dependencia `requiere("procesos.editar")`. `/api/me` devuelve los permisos y el frontend oculta lo que no aplique (la API igual lo bloquea).
- Roles semilla editables: Administrador, Juez, Secretario, Escribiente, Consulta. Pantallas nuevas en Configuración: Usuarios y Roles.
- El tema (claro/oscuro, color, letra) pasa a ser preferencia por usuario.

## Respaldo y restauración

- **Exportar**: JSON con `{formato: "control-procesos", version: 3, generado, procesos, actuaciones, config, plantillas, roles, usuarios}`. Se guarda con diálogo nativo "Guardar como".
- **Restaurar**: valida el esquema, hace un respaldo automático previo y reemplaza todo en una sola transacción. Usuarios y roles solo se restauran si se marca la opción.
- **Formato viejo**: si el JSON no trae `formato` pero sí `procesos` y `actuaciones`, se trata como exportación del HTML: se conservan los ids, se convierte `config` a las tablas nuevas y no se tocan los usuarios.
- **Automático**: tarea diaria en el servidor que escribe en `%PROGRAMDATA%\ControlProcesos\backups\` con rotación (últimos 30). Hora y cantidad configurables.

## Fases

0. **Base y prueba de concepto**: `git init`, `pyproject.toml`, esqueleto FastAPI + pywebview. Probar en Windows lo dudoso: `window.print()`/PDF dentro de WebView2 y guardar archivos (JSON/CSV) vía `js_api`. Si la impresión falla, el plan B es abrir el documento en el navegador del sistema.
1. **Dominio y BD**: modelos, migración inicial, seeds; portar a Python calendario, términos, estados, rutas, plantillas y fecha en letras, con pruebas.
2. **API**: autenticación, sesiones, permisos, CRUD de procesos/actuaciones/configuración, tablero y paquetes, auditoría.
3. **Frontend**: partir el HTML, capa `api.js`, login, adaptar las cinco vistas y los modales, pantallas de usuarios/roles/auditoría, reemplazar los `prompt()` de firmantes y pasos por modales.
4. **Respaldos**: exportar, restaurar, formato viejo, automáticos.
5. **Escritorio y empaquetado**: asistente Servidor/Cliente (config en `%APPDATA%`), bandeja, PyInstaller, instalador Inno Setup con acceso directo y regla de firewall para el puerto.
6. **Verificación final** en dos equipos Windows.

## Verificación

- **Pruebas unitarias del dominio**: casos tomados del HTML (los 17 ejemplos de `seed()`) ejecutando las funciones JS originales con Node para generar valores esperados de `codigo`, `vencimiento` y `estTermino`, y compararlos contra Python. Casos de borde del calendario: festivos, suspensiones, día reabierto.
- **Pruebas de API** con `TestClient`: cada permiso permite/bloquea lo que debe, conflicto 409, auditoría registra antes/después.
- **Respaldo**: exportar → vaciar → restaurar deja la BD idéntica; importar un JSON real exportado desde `control_procesos.html`.
- **Manual en Windows**: instalar en equipo A como servidor, crear admin, cargar ejemplos; instalar en equipo B como cliente, entrar con un usuario "Consulta" y confirmar que no puede editar; editar la misma actuación desde ambos; generar constancia y pase y guardarlos como PDF; imprimir y exportar un paquete.

## Pilas

- **El `.exe` solo se puede construir en Windows** (PyInstaller no compila cruzado desde macOS). Se necesita un equipo Windows o un runner de GitHub Actions; el desarrollo diario sí se puede hacer en Mac.
- Los clientes requieren WebView2 (viene en Windows 10/11 actualizados; el instalador lo verifica).
- El tráfico en la red local va por HTTP sin cifrar. Aceptable para una LAN de oficina; HTTPS con certificado propio queda como mejora.
- Las notas del proceso dicen hoy "solo suyas"; en multiusuario quedan compartidas por proceso y protegidas por el permiso `procesos.notas`.
- Los festivos están cargados hasta 2030; se dejan editables en Configuración.
