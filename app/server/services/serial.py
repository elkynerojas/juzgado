from datetime import date, datetime

from app.server.domain import estados as E
from app.server.domain.rutas import siguiente_paso

OCULTOS = {"password_hash"}


def a_dict(obj) -> dict:
    out = {}
    for col in obj.__table__.columns:
        if col.name in OCULTOS:
            continue
        v = getattr(obj, col.name)
        if isinstance(v, (date, datetime)):
            v = v.isoformat()
        elif isinstance(v, bytes):
            v = f"<{len(v)} bytes>"
        out[col.name] = v
    return out


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def derivado_act(a, ctx: E.Contexto) -> dict:
    c = E.codigo(a, ctx)
    ti = E.term_info(a, ctx)
    texto, badge = E.resultado(a, c, ctx)
    return {
        "codigo": c,
        "situacion": E.SIT[c],
        "badge": E.SIT_BADGE[c],
        "ubicacion": E.ubicacion(c),
        "dias": E.dias_estado(a, c, ctx),
        "fecha_activa": iso(E.fecha_activa(a, ctx)),
        "vencimiento": iso(E.vencimiento(a, ctx)),
        "est_termino": E.est_termino(a, ctx),
        "termino_info": {"dias": ti.dias, "habil": ti.habil} if ti else None,
        "resultado": {"texto": texto, "badge": badge},
    }


def act_dict(a, ctx: E.Contexto, hermanas=None, rutas=None) -> dict:
    d = a_dict(a)
    d["derivado"] = derivado_act(a, ctx)
    if hermanas is not None and rutas is not None:
        s = siguiente_paso(a, hermanas, rutas)
        d["siguiente"] = (
            {"ruta_id": s.ruta.id, "ruta": s.ruta.nombre, "idx": s.idx, "paso": paso_dict(s.paso)} if s else None
        )
    return d


def paso_dict(p) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "materia": p.materia,
        "origen": p.origen,
        "termino": p.termino,
        "descripcion": p.descripcion,
    }


def proc_dict(p, d: E.ProcDeriv) -> dict:
    out = a_dict(p)
    out["derivado"] = {
        "vivas": d.vivas,
        "rep_despacho": d.rep_despacho,
        "rep_secretaria": d.rep_secretaria,
        "en_secretaria": d.en_secretaria,
        "en_despacho": d.en_despacho,
        "inactividad": d.inactividad,
        "proximo": iso(d.proximo),
        "dias_sin_mov": d.dias_sin_mov,
    }
    return out
