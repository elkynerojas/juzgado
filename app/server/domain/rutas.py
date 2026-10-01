from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.server.domain.estados import Contexto, codigo, est_termino


@dataclass(frozen=True)
class Siguiente:
    ruta: object
    idx: int
    paso: object


def paso_cerrado(a, ctx: Contexto) -> bool:
    """La actuación avanzó lo suficiente como para proponer el siguiente eslabón."""
    return codigo(a, ctx) in (0, 5, 6, 7) or est_termino(a, ctx) == "Vencido"


def _tiene_sucesor(a, acts_del_proceso: Iterable) -> bool:
    return any(
        x.cuaderno == a.cuaderno and x.ruta_id == a.ruta_id and x.paso_idx is not None and x.paso_idx > a.paso_idx
        for x in acts_del_proceso
    )


def siguiente_paso(a, acts_del_proceso: Iterable, rutas: Mapping[str, object]) -> Siguiente | None:
    if not a.ruta_id or a.paso_idx is None:
        return None
    ruta = rutas.get(a.ruta_id)
    if not ruta:
        return None
    idx = a.paso_idx + 1
    if idx >= len(ruta.pasos) or _tiene_sucesor(a, acts_del_proceso):
        return None
    return Siguiente(ruta, idx, ruta.pasos[idx])
