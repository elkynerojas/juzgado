# -*- mode: python ; coding: utf-8 -*-
# Se ejecuta desde la raíz del proyecto, en Windows:
#   uv run pyinstaller packaging/control_procesos.spec --noconfirm
# Deja la aplicación en dist/ControlProcesos/ (carpeta, no un solo archivo: arranca más rápido
# y da menos falsos positivos de antivirus).
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

raiz = Path(SPECPATH).parent
icono = raiz / "packaging" / "icono.ico"

# Los datos se copian con la misma ruta relativa que tienen en el proyecto: el código los busca
# a partir de __file__, que dentro del ejecutable apunta a la carpeta del paquete.
datos = [
    (str(raiz / "app" / "web"), "app/web"),
    (str(raiz / "app" / "server" / "db" / "seed"), "app/server/db/seed"),
    (str(raiz / "app" / "desktop" / "asistente.html"), "app/desktop"),
    (str(raiz / "migrations" / "env.py"), "migrations"),
    (str(raiz / "migrations" / "script.py.mako"), "migrations"),
    (str(raiz / "migrations" / "versions"), "migrations/versions"),
]

a = Analysis(
    [str(raiz / "packaging" / "entrada.py")],
    pathex=[str(raiz)],
    datas=datos,
    # uvicorn y pystray eligen implementación por nombre en tiempo de ejecución; las migraciones
    # se cargan como archivos sueltos, así que sus importaciones tampoco se detectan solas.
    hiddenimports=collect_submodules("uvicorn") + collect_submodules("app") + ["pystray._win32", "alembic.op", "sqlalchemy.dialects.sqlite"],
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="ControlProcesos",
    console=False,
    icon=str(icono) if icono.exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ControlProcesos")
