"""Respaldo automático diario. Corre en un hilo del servidor mientras la app está abierta."""

import logging
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.server.db.models import Config
from app.server.services import respaldo

log = logging.getLogger(__name__)

ACTIVO, HORA, CONSERVAR, ULTIMO = "respaldo_activo", "respaldo_hora", "respaldo_conservar", "respaldo_ultimo"
DEFECTO = {ACTIVO: "1", HORA: "18:00", CONSERVAR: "30"}
CONSERVAR_PREVIOS = 10
INTERVALO_S = 60


def _leer(s: Session, clave: str) -> str:
    c = s.get(Config, clave)
    return c.valor if c else DEFECTO.get(clave, "")


def _escribir(s: Session, clave: str, valor: str) -> None:
    s.merge(Config(clave=clave, valor=valor))


def leer_programacion(s: Session) -> dict:
    return {
        "activo": _leer(s, ACTIVO) == "1",
        "hora": _leer(s, HORA),
        "conservar": int(_leer(s, CONSERVAR)),
        "ultimo": _leer(s, ULTIMO) or None,
    }


def guardar_programacion(s: Session, activo: bool, hora: str, conservar: int) -> None:
    _escribir(s, ACTIVO, "1" if activo else "0")
    _escribir(s, HORA, hora)
    _escribir(s, CONSERVAR, str(conservar))


def respaldar_ahora(s: Session, directorio: Path, momento: datetime | None = None) -> Path:
    ruta = respaldo.guardar_archivo(directorio, respaldo.PREFIJO_AUTO, respaldo.exportar(s), momento)
    respaldo.rotar(directorio, respaldo.PREFIJO_AUTO, int(_leer(s, CONSERVAR)))
    return ruta


def tarea_diaria(sesiones: sessionmaker[Session], directorio: Path, momento: datetime) -> Path | None:
    """Hace el respaldo del día si ya pasó la hora programada y aún no se ha hecho hoy."""
    with sesiones() as s:
        p = leer_programacion(s)
        hoy = momento.date().isoformat()
        if not p["activo"] or p["ultimo"] == hoy or momento.strftime("%H:%M") < p["hora"]:
            return None
        ruta = respaldar_ahora(s, directorio, momento)
        _escribir(s, ULTIMO, hoy)
        s.commit()
        return ruta


def iniciar(sesiones: sessionmaker[Session], directorio: Path) -> threading.Event:
    detener = threading.Event()

    def ciclo():
        while not detener.wait(INTERVALO_S):
            try:
                ruta = tarea_diaria(sesiones, directorio, datetime.now())
                if ruta:
                    log.info("Respaldo automático: %s", ruta)
            except Exception:
                log.exception("Falló el respaldo automático")

    threading.Thread(target=ciclo, daemon=True, name="respaldo-diario").start()
    return detener
