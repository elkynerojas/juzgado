from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def actualizar(engine: Engine) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.begin() as conexion:
        cfg.attributes["connection"] = conexion
        command.upgrade(cfg, "head")
