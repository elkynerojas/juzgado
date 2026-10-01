"""Configuración de este equipo: si es el servidor o un cliente, y a dónde se conecta."""

import json
import os
import sys
from pathlib import Path

ENV_CONFIG = "CONTROL_PROCESOS_CONFIG"
SERVIDOR, CLIENTE = "servidor", "cliente"
PUERTO = 8765


def dir_local() -> Path:
    if os.environ.get(ENV_CONFIG):
        base = Path(os.environ[ENV_CONFIG])
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "ControlProcesos"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "ControlProcesos"
    else:
        base = Path.home() / ".config" / "control-procesos"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _archivo() -> Path:
    return dir_local() / "config.json"


def leer() -> dict | None:
    try:
        cfg = json.loads(_archivo().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if cfg.get("modo") == SERVIDOR and isinstance(cfg.get("puerto"), int):
        return {"modo": SERVIDOR, "puerto": cfg["puerto"]}
    if cfg.get("modo") == CLIENTE and isinstance(cfg.get("url"), str) and cfg["url"]:
        return {"modo": CLIENTE, "url": cfg["url"]}
    return None


def guardar(cfg: dict) -> None:
    _archivo().write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def borrar() -> None:
    _archivo().unlink(missing_ok=True)
