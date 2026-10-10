"""Comparación difusa de etiquetas del formato SIERJU (puerto literal de la v2 del HTML).

El formato oficial nombra filas y columnas con textos largos ("(FIL4207) ARTÍCULO 120. LESIONES CULPOSAS."),
así que la clasificación no puede ser por igualdad: se normaliza y se puntúa el parecido. La aritmética y el
orden de recorrido son los mismos de `statBest`, para que Python elija exactamente la misma etiqueta que la v2.
"""

import re
import unicodedata
from functools import lru_cache

# palabras que no distinguen una fila de otra
VACIAS = frozenset(
    ("DEL", "LOS", "LAS", "POR", "PARA", "CON", "UNA", "UNO", "OTRO", "OTROS", "OTRAS", "TIPO", "PROCESO", "PROCESOS")
)
UMBRAL = 7

_PARENTESIS = re.compile(r"\([^)]*\)")
_NO_ALNUM = re.compile(r"[^A-Z0-9]+")
# el prefijo que el formato pone a cada etiqueta; la v2 no tolera un salto de línea dentro y aquí tampoco,
# para no mover ninguna puntuación (ver limpiar_prefijo)
_PREFIJO = re.compile(r"^\((?:FIL|COL)\d+\)\s*")


@lru_cache(maxsize=None)
def norm(s: str | None) -> str:
    """Sin tildes, en mayúsculas, sin paréntesis ni signos."""
    base = unicodedata.normalize("NFD", str(s or ""))
    sin_tildes = "".join(c for c in base if not unicodedata.combining(c))
    sin_parentesis = _PARENTESIS.sub(" ", sin_tildes.upper())
    return _NO_ALNUM.sub(" ", sin_parentesis).strip()


def limpiar(s: str | None) -> str:
    """Quita el prefijo "(FIL1234)" exactamente como la v2: igual de estricto, para no alterar las puntuaciones."""
    return _PREFIJO.sub("", str(s or "")).strip()


# la etiqueta de COL6828 trae un salto de línea dentro del paréntesis y `limpiar` no lo quita (igual que la v2).
# Para mostrarla a una persona sí hay que quitarlo.
_PREFIJO_TOLERANTE = re.compile(r"^\((?:FIL|COL)\s*\d+\s*\)\s*", re.S)


def para_mostrar(s: str | None) -> str:
    return " ".join(_PREFIJO_TOLERANTE.sub("", str(s or "")).split())


@lru_cache(maxsize=None)
def tokens(s: str | None) -> tuple[str, ...]:
    return tuple(x for x in norm(s).split() if len(x) > 2 and x not in VACIAS)


def puntuar(etiqueta: str, consulta: str) -> float:
    """Lo que `statBest` calcula para una etiqueta: exacto 100, contenido 60+, y si no, tokens en común."""
    limpia = limpiar(etiqueta)
    nx, ne = norm(limpia), norm(consulta)
    if nx == ne:
        return 100.0
    if nx in ne or ne in nx:
        return 60 + min(len(nx), len(ne)) / 20
    xt, qt = tokens(limpia), tokens(consulta)
    comunes = sum(1 for t in qt if t in xt)
    s = comunes * 8 - abs(len(xt) - len(qt)) * 0.2
    if qt and comunes == len(qt):
        s += 12
    return s


def mejor(etiquetas, consulta: str | None) -> str:
    """La etiqueta que más se parece, o "" si ninguna llega al umbral.

    Desempata por orden de la lista (`s > bs` estricto), igual que la v2.
    """
    if not etiquetas or not consulta:
        return ""
    elegida, mejor_puntaje = "", -1.0
    for x in etiquetas:
        s = puntuar(x, consulta)
        if s > mejor_puntaje:
            mejor_puntaje, elegida = s, x
    return elegida if mejor_puntaje >= UMBRAL else ""
