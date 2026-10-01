import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.server.app import create_app
from app.server.db.migrate import actualizar
from app.server.db.session import crear_engine, crear_sesiones
from app.server.domain.calendario import Calendario

GOLDEN = Path(__file__).parent / "golden"


def golden(nombre: str):
    return json.loads((GOLDEN / nombre).read_text(encoding="utf-8"))


def f(s) -> date | None:
    return date.fromisoformat(s) if s else None


def iso(d) -> str | None:
    return d.isoformat() if d else None


def calendario_de_js(festivos, c) -> Calendario:
    return Calendario(
        festivos=frozenset(f(x) for x in festivos),
        suspensiones=tuple((f(r["desde"]), f(r["hasta"])) for r in c["suspensiones"]),
        cerrados=frozenset(f(x) for x in c["cerrados"]),
        reabiertos=frozenset(f(x) for x in c["reabiertos"]),
    )


@pytest.fixture
def sesion(tmp_path):
    engine = crear_engine(tmp_path / "prueba.db")
    actualizar(engine)
    with crear_sesiones(engine)() as s:
        yield s
    engine.dispose()


ADMIN = {"usuario": "admin", "nombre": "Administradora", "password": "clave-segura-1"}


@pytest.fixture
def app(tmp_path):
    engine = crear_engine(tmp_path / "api.db")
    yield create_app(engine, respaldos=tmp_path / "backups")
    engine.dispose()


@pytest.fixture
def cliente(app):
    """Cliente sin sesión."""
    return TestClient(app)


@pytest.fixture
def admin(app):
    """Cliente con sesión de administrador (hace la instalación inicial)."""
    c = TestClient(app)
    assert c.post("/api/instalacion", json=ADMIN).status_code == 201
    return c


@pytest.fixture
def crear_usuario(app, admin):
    """Crea un usuario con el rol dado y devuelve un cliente con su sesión."""

    def _crear(usuario: str, rol: str, password: str = "clave-segura-2") -> TestClient:
        roles = {x["nombre"]: x["id"] for x in admin.get("/api/roles").json()}
        r = admin.post("/api/usuarios", json={"usuario": usuario, "nombre": usuario, "password": password, "rol_id": roles[rol]})
        assert r.status_code == 201, r.text
        c = TestClient(app)
        assert c.post("/api/auth/login", json={"usuario": usuario, "password": password}).status_code == 200
        return c

    return _crear
