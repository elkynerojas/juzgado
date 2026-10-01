from dataclasses import dataclass, field
from datetime import date, timedelta

MAX_ITERACIONES = 4000


@dataclass(frozen=True)
class Calendario:
    festivos: frozenset[date] = frozenset()
    suspensiones: tuple[tuple[date, date], ...] = ()
    cerrados: frozenset[date] = frozenset()
    reabiertos: frozenset[date] = field(default_factory=frozenset)


def es_habil(d: date, cal: Calendario) -> bool:
    if d.weekday() >= 5:
        return False
    if any(desde <= d <= hasta for desde, hasta in cal.suspensiones):
        return False
    if d in cal.cerrados:
        return False
    # un día reabierto solo levanta un festivo; no habilita fines de semana ni suspensiones
    if d in cal.festivos and d not in cal.reabiertos:
        return False
    return True


def calc_venc(inicio: date | None, dias: int | None, habil: bool, cal: Calendario) -> date | None:
    if not inicio or not dias:
        return None
    if not habil:
        return inicio + timedelta(days=dias)
    d = inicio
    contados = 0
    for _ in range(MAX_ITERACIONES):
        if contados >= dias:
            break
        d += timedelta(days=1)
        if es_habil(d, cal):
            contados += 1
    return d
