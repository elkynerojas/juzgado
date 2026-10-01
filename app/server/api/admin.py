from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, requiere
from app.server.db.models import Actuacion, Auditoria, Proceso, Usuario
from app.server.services import auditoria, ejemplos
from app.server.services.serial import a_dict

r = APIRouter(prefix="/api", tags=["administración"])


@r.get("/auditoria")
def listar_auditoria(
    entidad: str = "",
    entidad_id: str = "",
    usuario: str = "",
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(100, ge=1, le=500),
    saltar: int = Query(0, ge=0),
    s: Session = Depends(get_db),
    _=Depends(requiere("auditoria.ver")),
):
    filtros = []
    if entidad:
        filtros.append(Auditoria.entidad == entidad)
    if entidad_id:
        filtros.append(Auditoria.entidad_id == entidad_id)
    if usuario:
        filtros.append(Auditoria.usuario_nombre == usuario)
    if desde:
        filtros.append(Auditoria.fecha >= datetime.combine(desde, time.min))
    if hasta:
        filtros.append(Auditoria.fecha < datetime.combine(hasta + timedelta(days=1), time.min))
    total = s.scalar(select(func.count()).select_from(Auditoria).where(*filtros))
    filas = s.scalars(
        select(Auditoria).where(*filtros).order_by(Auditoria.fecha.desc(), Auditoria.id.desc()).limit(limite).offset(saltar)
    )
    return {"total": total, "filas": [a_dict(x) for x in filas]}


def _conteo(s: Session) -> dict:
    return {
        "procesos": s.scalar(select(func.count()).select_from(Proceso)),
        "actuaciones": s.scalar(select(func.count()).select_from(Actuacion)),
    }


@r.post("/datos/ejemplos")
def cargar_ejemplos(s: Session = Depends(get_db), u: Usuario = Depends(requiere("respaldo.restaurar"))):
    """Reemplaza todos los procesos y actuaciones por los datos de ejemplo."""
    antes = _conteo(s)
    ejemplos.cargar_ejemplos(s)
    s.flush()
    despues = _conteo(s)
    auditoria.registrar(s, u, "datos", "ejemplos", auditoria.CREAR, antes=antes, despues=despues)
    s.commit()
    return despues


@r.post("/datos/vaciar")
def vaciar(s: Session = Depends(get_db), u: Usuario = Depends(requiere("respaldo.vaciar"))):
    antes = _conteo(s)
    ejemplos.vaciar(s)
    auditoria.registrar(s, u, "datos", "vaciar", auditoria.ELIMINAR, antes=antes)
    s.commit()
    return _conteo(s)
