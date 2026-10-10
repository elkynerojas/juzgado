# Control de Procesos

Aplicación de escritorio para llevar el control de procesos judiciales de un despacho: qué actuaciones están pendientes, en manos de quién (secretaría o despacho), qué términos están corriendo y cuándo vencen.

Funciona en Windows como aplicación nativa y es multiusuario: un equipo hace de **servidor** y guarda la información; los demás se conectan como **clientes** por la red local.

Nació como la migración de `legacy/control_procesos.html`, una página de un solo archivo que guardaba todo en el navegador de un único equipo.

## Qué hace

- **Procesos y actuaciones**, organizadas por cuaderno, con las fechas de su ciclo: memorial, constancia, pase al despacho, providencia, ejecutoria y cumplimiento.
- **Procesos penales, tutelas y constitucionales**: naturaleza del proceso, solicitudes de control de garantías, delitos, tutela con impugnación, desacato y hábeas corpus, con actuaciones que se crean solas según la naturaleza.
- **Situación calculada**: a partir de esas fechas, cada actuación queda clasificada (sin constancia, falta pasar al despacho, al despacho pendiente de proveer, corre ejecutoria…) y ubicada en secretaría o despacho.
- **Términos** en días hábiles judiciales o calendario, con festivos, suspensiones, días cerrados y días habilitados.
- **Tablero** con los represamientos y los próximos vencimientos.
- **Gestión por paquetes**: todas las actuaciones pendientes de una misma materia, para trabajarlas en una jornada; se imprime o se exporta a CSV.
- **Audiencias**: pestaña propia para fijarlas, resolverlas o reprogramarlas, con contador y aviso de las pendientes por confirmar.
- **Estadística SIERJU**: los datos del formulario trimestral se calculan de los procesos y actuaciones del periodo, con datos especiales para lo que no sale solo; se descarga el Excel oficial con su formato, el Excel completo y una bitácora en CSV.
- **Rutas procesales**: secuencias de pasos que proponen la siguiente actuación al cerrar la anterior.
- **Constancias y pases al despacho** desde plantillas, con membrete y antefirma, listos para imprimir o guardar como PDF.
- **Usuarios, roles y permisos**: 30 permisos asignables por rol, con cinco roles iniciales.
- **Auditoría**: quién creó, cambió o eliminó cada dato, con el antes y el después.
- **Respaldos** en JSON: exportar, restaurar, respaldo automático diario y lectura del formato del HTML original (v1 y v2).
- **Datos de ejemplo** para conocer la aplicación sin cargar procesos reales.
- **Ayuda**: manual de usuario en PDF y datos de la versión, desde el menú.

## Arquitectura

```
[Equipo servidor]                          [Equipos cliente]
 ventana nativa ──► http://127.0.0.1:8765    ventana nativa ──► http://IP-servidor:8765
 FastAPI + uvicorn
 SQLite
```

Un solo programa cumple los dos papeles. En el primer arranque cada equipo elige si es servidor o cliente.

| Capa | Tecnología |
|---|---|
| Ventana | pywebview (WebView2 en Windows) |
| Interfaz | HTML, CSS y JavaScript sin dependencias ni compilación |
| API | FastAPI + uvicorn |
| Datos | SQLite con SQLAlchemy 2 y migraciones de Alembic |
| Contraseñas | Argon2 |
| Empaquetado | PyInstaller + Inno Setup |

Las reglas de negocio viven solo en Python (`app/server/domain/`). La API entrega cada actuación y proceso con su situación ya calculada, y la interfaz se limita a mostrarla.

## Estructura

```
app/
  main.py            arranque y opciones de línea de comandos
  desktop/           ventana, asistente Servidor/Cliente, bandeja de Windows
  server/
    api/             endpoints: sesión, usuarios, procesos, audiencias, estadística, configuración, documentos, respaldo
    core/            permisos, seguridad, rutas de datos
    db/              modelos, semillas y datos por defecto
    domain/          calendario, términos, situaciones, rutas, plantillas, naturaleza,
                     automatismos, audiencias; sierju/ arma la estadística
    services/        auditoría, respaldos, respaldo automático, documentos, ejemplos,
                     Excel del SIERJU
  web/               interfaz; ayuda/ tiene el manual en PDF
docs/                manual de usuario: manual.md (texto fuente) y el .docx con capturas
migrations/          migraciones de la base de datos
packaging/           spec de PyInstaller, instalador y script de construcción
scripts/             utilidades de Node que leen el HTML original
tests/               pruebas; golden/ tiene los valores generados con el código original
legacy/              el HTML original, como referencia
```

## Desarrollo

Requiere [uv](https://docs.astral.sh/uv/); la versión de Python (3.12) la instala uv.

```bash
uv sync                               # instala dependencias
uv run pytest                         # pruebas
uv run control-procesos               # abre la aplicación en ventana
uv run control-procesos --sin-ventana # solo servidor: http://localhost:8765
```

Con `--sin-ventana`, la documentación interactiva de la API queda en `http://localhost:8765/api/docs`.

Otras opciones: `--cliente URL` abre la ventana contra un servidor sin cambiar la configuración del equipo, y `--reconfigurar` vuelve a mostrar el asistente Servidor/Cliente.

En desarrollo los datos quedan en `~/.control_procesos/`. Para usar otra carpeta, defina `CONTROL_PROCESOS_DATOS`.

### Pruebas contra el código original

Las reglas de cálculo se verifican contra el JavaScript del HTML original. Los scripts de `scripts/` ejecutan ese código con Node y guardan los resultados en `tests/golden/`; las pruebas comparan la versión en Python contra esos valores.

```bash
node scripts/generar_golden.mjs           # valores esperados de situaciones, términos y fechas
node scripts/generar_respaldo_legacy.mjs  # un respaldo en el formato del HTML original
node scripts/extraer_semillas.mjs         # catálogos por defecto, membrete, antefirma y plantilla SIERJU
node scripts/generar_golden_v2.mjs        # valores esperados de la v2: naturaleza, secretaría, automatismos
node scripts/generar_golden_sierju.mjs    # valores esperados de la estadística SIERJU y su Excel
```

Solo hay que volver a correrlos si cambia el HTML original (`legacy/control_procesos.html` o `legacy/control_procesos_v2.html`).

### Cambios en la base de datos

Después de modificar `app/server/db/models.py`:

```bash
uv run alembic revision --autogenerate -m "descripción del cambio"
```

La aplicación aplica las migraciones pendientes al arrancar.

## Construir el instalador

Solo se puede en Windows, porque PyInstaller no compila para otro sistema:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\construir.ps1
```

El resultado queda en `dist\ControlProcesos-Setup-<versión>.exe`. También lo construye el flujo **Windows** de GitHub Actions (`.github/workflows/windows.yml`).

## Documentación

- [docs/manual.md](docs/manual.md): manual operativo para el personal del juzgado. De él sale el manual en Word (`docs/`) y el PDF que abre *Ayuda → Manual de usuario* (`app/web/ayuda/`).
- [INSTALACION.md](INSTALACION.md): instalación del servidor y de los clientes, actualización y solución de problemas.
- [PLANEACION.md](PLANEACION.md): plan del proyecto, decisiones de diseño y estado por fase.

## Estado

Versión 1.2.0: se suman los procesos penales y constitucionales, las audiencias y la estadística SIERJU de la v2 del HTML. Las pruebas pasan en Windows y el instalador se construye: `dist\ControlProcesos-Setup-1.2.0.exe`. Falta verificar en el despacho la impresión y PDF, el guardado de archivos (incluidas las descargas del SIERJU), el icono de bandeja y la conexión entre dos equipos.
