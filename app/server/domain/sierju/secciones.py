"""Las 31 secciones del formato SIERJU y la búsqueda de sus filas y columnas."""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.server.db.seeds import cargar_mapa_plantilla, cargar_secciones_sierju, cargar_sierju
from app.server.domain.sierju.texto import mejor, norm, para_mostrar

# tolerante al salto de línea que la etiqueta de COL6828 trae dentro del paréntesis
RX_FIL = re.compile(r"\(FIL\s*(\d+)\s*\)")
RX_COL = re.compile(r"\(COL\s*(\d+)\s*\)")


@dataclass(frozen=True)
class Seccion:
    n: int
    code: str
    sheet: str
    title: str
    filas: tuple[str, ...]
    columnas: tuple[str, ...]
    # código -> etiqueta, para ubicar una columna por su número cuando el texto no basta
    por_codigo: dict[str, str] = field(default_factory=dict)

    def etiqueta_fila(self, fila: str) -> str:
        return para_mostrar(fila)


def _codigos(etiquetas, rx) -> dict[str, str]:
    out = {}
    for e in etiquetas:
        if m := rx.search(e):
            out.setdefault(f"{'FIL' if rx is RX_FIL else 'COL'}{m[1]}", e)
    return out


def _construir() -> dict[str, Seccion]:
    out = {}
    for s in cargar_secciones_sierju():
        filas, cols = tuple(s["rows"]), tuple(s["cols"])
        out[s["code"]] = Seccion(
            n=s["n"],
            code=s["code"],
            sheet=s["sheet"],
            title=s["title"],
            filas=filas,
            columnas=cols,
            por_codigo=_codigos(filas, RX_FIL) | _codigos(cols, RX_COL),
        )
    return out


SECCIONES: dict[str, Seccion] = _construir()

# solo las que la plantilla oficial sabe llenar; las demás existen pero no llegan al Excel (igual que activeSecs)
ACTIVAS: tuple[Seccion, ...] = tuple(
    sorted((SECCIONES[c] for c in cargar_mapa_plantilla()["mapa"] if c in SECCIONES), key=lambda s: s.n)
)

ALIAS_COLUMNAS: dict[str, list[str]] = cargar_sierju()["alias_columnas"]


@lru_cache(maxsize=None)
def buscar_fila(code: str, consulta: str | None) -> str:
    """Como `statFindRow`: si no engancha y la consulta habla de "otro", cae en la fila de otros."""
    s = SECCIONES.get(code)
    if not s:
        return ""
    if r := mejor(s.filas, consulta):
        return r
    if consulta and "OTRO" in norm(consulta):
        return mejor(s.filas, "OTROS")
    return ""


@lru_cache(maxsize=None)
def buscar_columna(code: str, consulta: str | None) -> str:
    """Como `statFindCol`: si el texto no engancha, se reintenta con los alias del formato.

    Un alias aplica cuando su nombre y la consulta se contienen mutuamente, no por igualdad.
    """
    s = SECCIONES.get(code)
    if not s:
        return ""
    if r := mejor(s.columnas, consulta):
        return r
    if not consulta:
        return ""
    nq = norm(consulta)
    for clave, grupo in ALIAS_COLUMNAS.items():
        nk = norm(clave)
        if nk in nq or nq in nk:
            for alias in grupo:
                if r := mejor(s.columnas, alias):
                    return r
    return ""


def columna_por_codigo(code: str, codigo_col: str) -> str:
    s = SECCIONES.get(code)
    return s.por_codigo.get(codigo_col, "") if s else ""
