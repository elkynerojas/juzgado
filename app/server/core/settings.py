import os
import sys
from pathlib import Path

ENV_DATOS = "CONTROL_PROCESOS_DATOS"


def dir_datos() -> Path:
    if os.environ.get(ENV_DATOS):
        base = Path(os.environ[ENV_DATOS])
    elif sys.platform == "win32":
        base = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "ControlProcesos"
    else:
        base = Path.home() / ".control_procesos"
    base.mkdir(parents=True, exist_ok=True)
    return base


def ruta_bd() -> Path:
    return dir_datos() / "control_procesos.db"
