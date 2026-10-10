"""Los eventos agrupados por sección, fila y columna: lo que se pinta y lo que llena el Excel."""

from dataclasses import dataclass

from app.server.domain.sierju.eventos import Paquete
from app.server.domain.sierju.secciones import ACTIVAS, Seccion


@dataclass(frozen=True)
class MatrizSeccion:
    seccion: Seccion
    # fila -> columna -> cantidad; todas las filas del formato existen, aunque estén en cero
    mapa: dict[str, dict[str, int]]
    total: int


def construir(paquete: Paquete) -> list[MatrizSeccion]:
    """Una matriz por sección que la plantilla oficial sabe llenar, en el orden del formato."""
    out = []
    for sec in ACTIVAS:
        mapa: dict[str, dict[str, int]] = {f: {} for f in sec.filas}
        total = 0
        for e in paquete.eventos:
            if e.seccion != sec.code:
                continue
            mapa.setdefault(e.fila, {})
            mapa[e.fila][e.columna] = mapa[e.fila].get(e.columna, 0) + (e.cantidad or 0)
            total += e.cantidad or 0
        out.append(MatrizSeccion(seccion=sec, mapa=mapa, total=total))
    return out
