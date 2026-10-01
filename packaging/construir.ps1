# Construye el ejecutable y el instalador. Se corre en Windows, desde la raíz del proyecto:
#   powershell -ExecutionPolicy Bypass -File packaging\construir.ps1
# Requiere uv (https://docs.astral.sh/uv/) e Inno Setup 6 (https://jrsoftware.org/isinfo.php).
$ErrorActionPreference = "Stop"

uv sync --group dev --group build
if ($LASTEXITCODE) { exit $LASTEXITCODE }
uv run pytest -q
if ($LASTEXITCODE) { exit $LASTEXITCODE }
uv run python packaging/generar_icono.py
if ($LASTEXITCODE) { exit $LASTEXITCODE }
uv run pyinstaller packaging/control_procesos.spec --noconfirm
if ($LASTEXITCODE) { exit $LASTEXITCODE }

$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    Write-Host "No se encontró Inno Setup 6. La aplicación quedó en dist\ControlProcesos; falta solo el instalador."
    exit 1
}
& $iscc packaging\instalador.iss
if ($LASTEXITCODE) { exit $LASTEXITCODE }
Write-Host "Listo: dist\ControlProcesos-Setup-*.exe"
