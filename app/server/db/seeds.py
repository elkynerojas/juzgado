import json
from datetime import date
from functools import cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.core.permisos import ROL_ADMIN, ROLES_SEMILLA
from app.server.db.models import (
    Catalogo,
    Config,
    Festivo,
    Firmante,
    Plantilla,
    Rol,
    RolPermiso,
    Ruta,
    RutaPaso,
    Termino,
    TipoRuta,
)

SEED_DIR = Path(__file__).resolve().parent / "seed"
MARCA = "semilla"

# tipo de catálogo en la BD -> ruta de la lista dentro de catalogos.json
CATALOGOS = {
    "materias": ("materias",),
    "tipos_solicitud": ("tiposSolicitud",),
    "cuadernos": ("cuadernos",),
    "macroetapas": ("macroetapas",),
    "asuntos_civil": ("asuntos", "civil"),
    "asuntos_familia": ("asuntos", "familia"),
    "cargos": ("cargos",),
}


def cargar_catalogos() -> dict:
    return json.loads((SEED_DIR / "catalogos.json").read_text(encoding="utf-8"))


# Catálogos normativos de SIERJU y penales: de solo lectura, no se guardan en la BD.
@cache
def cargar_sierju() -> dict:
    return json.loads((SEED_DIR / "sierju.json").read_text(encoding="utf-8"))


@cache
def cargar_secciones_sierju() -> list[dict]:
    return json.loads((SEED_DIR / "sierju_secciones.json").read_text(encoding="utf-8"))


@cache
def cargar_mapa_plantilla() -> dict:
    return json.loads((SEED_DIR / "sierju_tpl_map.json").read_text(encoding="utf-8"))


PLANTILLA_SIERJU = SEED_DIR / "sierju_plantilla.xlsx"


def sembrar(s: Session) -> bool:
    """Carga los datos por defecto una sola vez. Devuelve True si sembró."""
    if s.get(Config, MARCA):
        return False
    d = cargar_catalogos()

    s.add_all(Festivo(fecha=date.fromisoformat(f)) for f in d["festivos"])
    s.add_all(Termino(orden=i, **t) for i, t in enumerate(d["terminos"]))
    for tipo, ruta in CATALOGOS.items():
        valores = d
        for clave in ruta:
            valores = valores[clave]
        s.add_all(Catalogo(tipo=tipo, valor=v, orden=i) for i, v in enumerate(dict.fromkeys(valores)))
    for i, r in enumerate(d["rutas"]):
        s.add(
            Ruta(
                id=r["id"],
                nombre=r["nombre"],
                descripcion=r.get("desc", ""),
                orden=i,
                pasos=[RutaPaso(orden=j, **p) for j, p in enumerate(r["pasos"])],
            )
        )
    s.flush()
    s.add_all(TipoRuta(tipo_solicitud=t, ruta_id=r) for t, r in d["tipoRuta"].items())
    s.add_all(Plantilla(**p) for p in d["plantillas"])
    s.add(
        Firmante(
            nombre=d["firmante"]["nombre"],
            cargo=d["firmante"]["cargo"],
            firma=(SEED_DIR / "antefirma.png").read_bytes(),
            firma_mime="image/png",
        )
    )
    s.add_all(Config(clave=k, valor=v) for k, v in d["juzgado"].items())
    s.add(Config(clave="membrete", valor="image/png", binario=(SEED_DIR / "membrete.png").read_bytes()))
    s.add(Config(clave=MARCA, valor="1"))
    s.commit()
    return True


def sembrar_roles(s: Session) -> bool:
    if s.scalar(select(Rol.id).limit(1)):
        return False
    for nombre, (descripcion, permisos) in ROLES_SEMILLA.items():
        rol = Rol(nombre=nombre, descripcion=descripcion, es_sistema=nombre == ROL_ADMIN)
        rol.permisos = [RolPermiso(permiso=p) for p in dict.fromkeys(permisos)]
        s.add(rol)
    s.commit()
    return True
