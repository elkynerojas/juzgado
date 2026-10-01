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

# Inno Setup puede quedar en Archivos de programa o, si se instaló con winget para un solo usuario, en AppData.
$candidatos = @()
$enPath = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($enPath) { $candidatos += $enPath.Source }
foreach ($clave in "HKLM:\SOFTWARE\WOW6432Node", "HKLM:\SOFTWARE", "HKCU:\SOFTWARE") {
    $reg = Get-ItemProperty "$clave\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" -ErrorAction SilentlyContinue
    if ($reg -and $reg.InstallLocation) { $candidatos += (Join-Path $reg.InstallLocation "ISCC.exe") }
}
$candidatos += "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
$candidatos += "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
$candidatos += "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
$iscc = $candidatos | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "No se encontro ISCC.exe (Inno Setup 6). Se busco en:"
    $candidatos | ForEach-Object { Write-Host "  $_" }
    Write-Host "La aplicacion quedo en dist\ControlProcesos; falta solo el instalador."
    exit 1
}
Write-Host "Inno Setup: $iscc"
& $iscc packaging\instalador.iss
if ($LASTEXITCODE) {
    Write-Host "Inno Setup termino con error $LASTEXITCODE (el detalle esta arriba)."
    exit $LASTEXITCODE
}
Write-Host "Listo:"
Get-ChildItem dist\ControlProcesos-Setup-*.exe | ForEach-Object { Write-Host "  $($_.FullName)" }
