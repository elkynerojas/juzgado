from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.server.core.settings import ruta_bd


def crear_engine(ruta: Path | str | None = None) -> Engine:
    engine = create_engine(f"sqlite:///{ruta or ruta_bd()}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas(conexion, _):
        cur = conexion.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def crear_sesiones(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
