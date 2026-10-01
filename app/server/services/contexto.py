from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.server.db.models import CalDia, CalSuspension, Festivo, Ruta, Termino
from app.server.domain.calendario import Calendario
from app.server.domain.estados import Contexto, TerminoInfo


def construir_calendario(s: Session) -> Calendario:
    dias = s.execute(select(CalDia.fecha, CalDia.tipo)).all()
    return Calendario(
        festivos=frozenset(s.scalars(select(Festivo.fecha))),
        suspensiones=tuple((d, h) for d, h in s.execute(select(CalSuspension.desde, CalSuspension.hasta))),
        cerrados=frozenset(f for f, t in dias if t == CalDia.CERRADO),
        reabiertos=frozenset(f for f, t in dias if t == CalDia.REABIERTO),
    )


def construir_contexto(s: Session, hoy: date | None = None) -> Contexto:
    terminos = {n: TerminoInfo(d, h) for n, d, h in s.execute(select(Termino.nombre, Termino.dias, Termino.habil))}
    return Contexto(hoy=hoy or date.today(), calendario=construir_calendario(s), terminos=terminos)


def mapa_rutas(s: Session) -> dict[str, Ruta]:
    rutas = s.scalars(select(Ruta).options(selectinload(Ruta.pasos)).order_by(Ruta.orden))
    return {r.id: r for r in rutas}
