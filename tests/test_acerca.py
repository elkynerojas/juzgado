import re
import tomllib
from pathlib import Path

from app.acerca import DESARROLLADOR, VERSION

RAIZ = Path(__file__).resolve().parent.parent


def test_acerca_sin_sesion(cliente):
    r = cliente.get("/api/acerca")
    assert r.status_code == 200
    assert r.json() == {"nombre": "Control de Procesos", "version": VERSION, "desarrollador": DESARROLLADOR}


def test_version_igual_en_proyecto_e_instalador():
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    instalador = re.search(r'#define Version "([^"]+)"', (RAIZ / "packaging" / "instalador.iss").read_text(encoding="utf-8")).group(1)
    assert VERSION == proyecto == instalador


def test_sirve_manual_pdf(cliente):
    r = cliente.get("/ayuda/Manual_de_usuario_Control_de_Procesos.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
