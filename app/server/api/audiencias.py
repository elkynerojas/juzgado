from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, obtener, requiere, usuario_actual, verificar_version
from app.server.api.esquemas import AudienciaIn, ResolverIn
from app.server.db.models import Actuacion, Proceso, Usuario
from app.server.domain import audiencias as Aud
from app.server.domain import naturaleza as N
from app.server.services import auditoria
from app.server.services.contexto import construir_contexto
from app.server.services.serial import a_dict, iso

r = APIRouter(prefix="/api/audiencias", tags=["audiencias"])


def _fila(a: Actuacion, p: Proceso) -> dict:
    return {
        "actuacion_id": a.id,
        "proceso_id": p.id,
        "radicado": p.radicado,
        "naturaleza": p.naturaleza,
        "area": N.area_de(p.naturaleza),
        "cuaderno": a.cuaderno,
        "aud_fecha": iso(a.aud_fecha),
        "aud_hora": a.aud_hora,
        "aud_tipo": a.aud_tipo,
        "aud_estado": Aud.estado_de(a),
        "aud_causa": a.aud_causa,
        "aud_inmediata": a.aud_inmediata,
        "asignado_a": a.asignado_a,
        "descripcion": a.descripcion,
        "version": a.version,
    }


def _todas(s: Session) -> tuple[list[Actuacion], dict[str, Proceso]]:
    procesos = {p.id: p for p in s.scalars(select(Proceso))}
    acts = [a for a in s.scalars(select(Actuacion)) if Aud.es_audiencia(a)]
    return acts, procesos


@r.get("")
def listar(
    desde: date | None = None,
    hasta: date | None = None,
    estado: str = "",
    area: str = "",
    s: Session = Depends(get_db),
    _=Depends(requiere("audiencias.ver")),
):
    hoy = construir_contexto(s).hoy
    acts, procesos = _todas(s)
    # las pendientes por confirmar se cuentan sobre todo, no sobre el rango elegido
    pendientes = [_fila(a, procesos[a.proceso_id]) for a in Aud.pendientes(acts, hoy)]
    kpis: dict[str, int] = defaultdict(int)
    filas = []
    for a in Aud.ordenar(acts):
        p = procesos[a.proceso_id]
        if desde and a.aud_fecha < desde:
            continue
        if hasta and a.aud_fecha > hasta:
            continue
        if estado and Aud.estado_de(a) != estado:
            continue
        if area and N.area_de(p.naturaleza) != area:
            continue
        kpis[Aud.estado_de(a)] += 1
        filas.append(_fila(a, p))
    return {
        "hoy": iso(hoy),
        "total": len(filas),
        "kpis": {e: kpis.get(e, 0) for e in Aud.ESTADOS},
        "pendientes": pendientes,
        "filas": filas,
    }


@r.get("/cuadernos/{pid}")
def cuadernos(pid: str, s: Session = Depends(get_db), _=Depends(requiere("audiencias.ver"))):
    """Los cuadernos del proceso: los suyos y los que ya usan sus actuaciones."""
    p = obtener(s, Proceso, pid, "Proceso")
    vistos = dict.fromkeys([p.cuaderno_inicial or "Principal", *(p.cuadernos or []), *(a.cuaderno for a in p.actuaciones)])
    return [c for c in vistos if c]


def _revisar_causa(p: Proceso, estado: str, causa: str) -> str:
    if estado not in Aud.ESTADOS:
        raise HTTPException(422, f"Estado de audiencia no válido: {estado}")
    if not Aud.lleva_causa(estado):
        return ""
    validas = Aud.causas(p.naturaleza, estado)
    if causa and causa not in validas:
        raise HTTPException(422, f"La causa «{causa}» no existe para este estado. No llegaría a la estadística.")
    return causa


@r.post("", status_code=201)
def crear(datos: AudienciaIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("audiencias.gestionar"))):
    p = obtener(s, Proceso, datos.proceso_id, "Proceso")
    causa = _revisar_causa(p, datos.estado, datos.causa)
    a = Aud.fijar(
        p,
        cuaderno=datos.cuaderno,
        fecha=datos.fecha,
        hora=datos.hora,
        tipo=datos.tipo,
        estado=datos.estado,
        causa=causa,
        asignado_a=datos.asignado_a,
    )
    a.creado_por = a.actualizado_por = u.id
    p.actuaciones.append(a)
    s.flush()
    auditoria.registrar(s, u, "actuacion", a.id, auditoria.CREAR, despues=a_dict(a))
    s.commit()
    return _fila(a, p)


@r.post("/{aid}/resolver")
def resolver(
    aid: str, datos: ResolverIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("audiencias.gestionar"))
):
    a = obtener(s, Actuacion, aid, "Audiencia")
    if not Aud.es_audiencia(a):
        raise HTTPException(422, "Esa actuación no es una audiencia con fecha.")
    p = a.proceso
    antes = a_dict(a)
    verificar_version(a, datos.version)
    causa = _revisar_causa(p, datos.estado, datos.causa)
    Aud.resolver(a, datos.estado, causa)
    a.version += 1
    a.actualizado_por = u.id

    nueva = None
    if datos.nueva_fecha:
        nueva = Aud.reprogramar(p, a, fecha=datos.nueva_fecha, hora=datos.nueva_hora, tipo=datos.nuevo_tipo)
        nueva.creado_por = nueva.actualizado_por = u.id
        p.actuaciones.append(nueva)
    s.flush()
    auditoria.registrar(s, u, "actuacion", a.id, auditoria.EDITAR, antes=antes, despues=a_dict(a))
    if nueva is not None:
        auditoria.registrar(s, u, "actuacion", nueva.id, auditoria.CREAR, despues=a_dict(nueva))
    s.commit()
    return {"actuacion": _fila(a, p), "nueva": _fila(nueva, p) if nueva is not None else None}
