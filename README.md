# Control de Procesos

Aplicación de escritorio para llevar el control de procesos judiciales de un despacho: qué actuaciones están pendientes, en manos de quién (secretaría o despacho), qué términos están corriendo y cuándo vencen.

Funciona en Windows como aplicación nativa y es multiusuario: un equipo hace de **servidor** y guarda la información; los demás se conectan como **clientes** por la red local.

Nació como la migración de `legacy/control_procesos.html`, una página de un solo archivo que guardaba todo en el navegador de un único equipo.

## Qué hace

- **Procesos y actuaciones**, organizadas por cuaderno, con las fechas de su ciclo: memorial, constancia, pase al despacho, providencia, ejecutoria y cumplimiento.
- **Situación calculada**: a partir de esas fechas, cada actuación queda clasificada (sin constancia, falta pasar al despacho, al despacho pendiente de proveer, corre ejecutoria…) y ubicada en secretaría o despacho.
- **Términos** en días hábiles judiciales o calendario, con festivos, suspensiones, días cerrados y días habilitados.
- **Tablero** con los represamientos y los próximos vencimientos.
- **Gestión por paquetes**: todas las actuaciones pendientes de una misma materia, para trabajarlas en una jornada; se imprime o se exporta a CSV.
- **Rutas procesales**: secuencias de pasos que proponen la siguiente actuación al cerrar la anterior.
- **Constancias y pases al despacho** desde plantillas, con membrete y antefirma, listos para imprimir o guardar como PDF.
- **Usuarios, roles y permisos**: 24 permisos asignables por rol, con cinco roles iniciales.
- **Auditoría**: quién creó, cambió o eliminó cada dato, con el antes y el después.
- **Respaldos** en JSON: exportar, restaurar, respaldo automático diario y lectura del formato del HTML original.

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
    api/             endpoints: sesión, usuarios, procesos, configuración, documentos, respaldo
    core/            permisos, seguridad, rutas de datos
    db/              modelos, semillas y datos por defecto
    domain/          calendario, términos, situaciones, rutas, plantillas
    services/        auditoría, respaldos, respaldo automático, documentos
  web/               interfaz
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
node scripts/extraer_semillas.mjs         # catálogos por defecto, membrete y antefirma
```

Solo hay que volver a correrlos si cambia `legacy/control_procesos.html`.

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

- [INSTALACION.md](INSTALACION.md): instalación del servidor y de los clientes, actualización y solución de problemas.
- [PLANEACION.md](PLANEACION.md): plan del proyecto, decisiones de diseño y estado por fase.

## Estado

El desarrollo está completo. Las pruebas pasan en Windows y el instalador ya se construye: `dist\ControlProcesos-Setup-1.1.exe`. Falta verificar en el despacho la impresión y PDF, el guardado de archivos, el icono de bandeja y la conexión entre dos equipos.
