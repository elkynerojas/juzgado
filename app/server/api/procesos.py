from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, obtener, permisos_de, requiere, usuario_actual, verificar_version
from app.server.api.esquemas import (
    ActuacionBase,
    ActuacionEdicion,
    ActuacionIn,
    NotasIn,
    ProcesoEdicion,
    ProcesoGuardado,
)
from app.server.db.models import Actuacion, Proceso, SolicitudPenal, Termino, Usuario
from app.server.domain import audiencias as Aud
from app.server.domain import automatismos as Auto
from app.server.domain import estados as E
from app.server.domain import naturaleza as N
from app.server.domain import secretaria as Sec
from app.server.services import auditoria
from app.server.services.contexto import construir_contexto, mapa_rutas
from app.server.services.serial import a_dict, act_dict, anio_de, derivado_act, iso, proc_dict, proceso_plano

r = APIRouter(prefix="/api", tags=["procesos"])

FILTROS = {
    "sc": lambda p, d: any(x.codigo == 3 for x in d.acts),
    "fp": lambda p, d: any(x.codigo == 4 for x in d.acts),
    "ad": lambda p, d: d.rep_despacho > 0,
    "rs": lambda p, d: d.rep_secretaria > 0,
    "esp": lambda p, d: any(x.codigo == 1 for x in d.acts),
    "susp": lambda p, d: p.situacion == "Suspendido",
}


def _todo(s: Session) -> tuple[list[Proceso], dict[str, list[Actuacion]]]:
    procesos = list(s.scalars(select(Proceso).order_by(Proceso.creado_en, Proceso.radicado)))
    por_proceso = defaultdict(list)
    for a in s.scalars(select(Actuacion).order_by(Actuacion.creado_en)):
        por_proceso[a.proceso_id].append(a)
    return procesos, por_proceso


def _partes(p: Proceso) -> str:
    return f"{p.demandante or ''} c/ {p.demandado or ''}"


def _fmt(d: date | None) -> str:
    return d.strftime("%d/%m/%y") if d else ""


# ---------- procesos ----------


UBIC_DESPACHO = "Despacho"
UBIC_SECRETARIA = "Secretaría"
UBIC_SIN = "Sin ubicación"


def _ubicacion(d: E.ProcDeriv) -> str:
    if d.en_despacho:
        return UBIC_DESPACHO
    if d.en_secretaria:
        return UBIC_SECRETARIA
    return UBIC_SIN


@r.get("/procesos")
def listar(
    q: str = "",
    filtro: str = "",
    anio: str = "",
    situacion: str = "",
    ubicacion: str = "",
    area: str = "",
    s: Session = Depends(get_db),
    _=Depends(requiere("procesos.ver")),
):
    ctx = construir_contexto(s)
    procesos, acts = _todo(s)
    q = q.lower().strip()
    filas = []
    for p in procesos:
        d = E.proc_deriv(p.situacion, acts[p.id], ctx)
        if filtro in FILTROS and not FILTROS[filtro](p, d):
            continue
        if anio and anio_de(p.radicado) != anio:
            continue
        if situacion and p.situacion != situacion:
            continue
        if ubicacion and _ubicacion(d) != ubicacion:
            continue
        if area and N.area_de(p.naturaleza) != area:
            continue
        if q:
            texto = " ".join([p.radicado, p.demandante, p.demandado, *(f"{a.materia} {a.descripcion}" for a in acts[p.id])])
            if q not in texto.lower():
                continue
        filas.append(proc_dict(p, d))
    # los selectores de filtro se llenan con lo que existe en la base, no con un catálogo fijo
    return {
        "filas": filas,
        "anios": sorted({a for p in procesos if (a := anio_de(p.radicado))}, reverse=True),
        "situaciones": sorted({p.situacion for p in procesos if p.situacion}),
        "ubicaciones": [UBIC_DESPACHO, UBIC_SECRETARIA, UBIC_SIN],
        "areas": list(N.AREAS),
    }


def _detalle(s: Session, p: Proceso, u: Usuario) -> dict:
    ctx = construir_contexto(s)
    acts = sorted(p.actuaciones, key=lambda a: a.creado_en)
    out = proc_dict(p, E.proc_deriv(p.situacion, acts, ctx))
    out["solicitudes_penales"] = proceso_plano(p)["solicitudes_penales"]
    out["actuaciones"] = []
    if "actuaciones.ver" in permisos_de(u):
        rutas = mapa_rutas(s)
        out["actuaciones"] = [act_dict(a, ctx, acts, rutas) for a in acts]
    return out


@r.get("/procesos/{pid}")
def detalle(pid: str, s: Session = Depends(get_db), u: Usuario = Depends(requiere("procesos.ver"))):
    return _detalle(s, obtener(s, Proceso, pid, "Proceso"), u)


def _nombres_terminos(s: Session) -> set[str]:
    return {n for (n,) in s.execute(select(Termino.nombre))}


def _aplicar_automatismos(s: Session, u: Usuario, p: Proceso, *, nuevo: bool, crear_inicial: bool) -> None:
    """Corre los automatismos de la v2 y deja en la sesión lo que crearon o cambiaron, ya auditado."""
    ctx = construir_contexto(s)
    acts = list(p.actuaciones)
    antes = {a.id: a_dict(a) for a in acts}
    nuevas = Auto.al_guardar_proceso(
        p, acts, ctx.calendario, _nombres_terminos(s), nuevo=nuevo, crear_inicial=crear_inicial
    )
    for a in nuevas:
        a.creado_por = a.actualizado_por = u.id
        Sec.autocompletar_actuacion(a, ctx.calendario)
        # se asocia por la relación, no con s.add: con delete-orphan una actuación suelta no se inserta
        p.actuaciones.append(a)
    s.flush()
    for a in nuevas:
        auditoria.registrar(s, u, "actuacion", a.id, auditoria.CREAR, despues=a_dict(a))
    # los automatismos también corrigen actuaciones ya guardadas; se comparan por diccionario porque
    # is_modified da falsos positivos en las columnas JSON
    for a in acts:
        despues = a_dict(a)
        if despues != antes[a.id]:
            a.version += 1
            a.actualizado_por = u.id
            auditoria.registrar(s, u, "actuacion", a.id, auditoria.EDITAR, antes=antes[a.id], despues=despues)


def _poner_solicitudes(p: Proceso, solicitudes) -> None:
    p.solicitudes_penales = [
        SolicitudPenal(**(x.model_dump(exclude={"id"}) | ({"id": x.id} if x.id else {})), orden=i)
        for i, x in enumerate(solicitudes)
    ]


@r.post("/procesos", status_code=201)
def crear(datos: ProcesoGuardado, s: Session = Depends(get_db), u: Usuario = Depends(requiere("procesos.crear"))):
    p = Proceso(**datos.columnas(), creado_por=u.id, actualizado_por=u.id)
    _poner_solicitudes(p, datos.solicitudes_penales)
    Auto.normalizar_proceso(p, date.today(), datos.crear_medidas)
    s.add(p)
    s.flush()
    auditoria.registrar(s, u, "proceso", p.id, auditoria.CREAR, despues=proceso_plano(p))
    _aplicar_automatismos(s, u, p, nuevo=True, crear_inicial=datos.crear_inicial)
    s.commit()
    return _detalle(s, p, u)


def _editar_proceso(s: Session, u: Usuario, pid: str, cambios: dict, version: int) -> dict:
    p = obtener(s, Proceso, pid, "Proceso")
    antes = a_dict(p)
    verificar_version(p, version)
    for k, v in cambios.items():
        setattr(p, k, v)
    p.actualizado_por = u.id
    s.flush()
    auditoria.registrar(s, u, "proceso", p.id, auditoria.EDITAR, antes=antes, despues=a_dict(p))
    s.commit()
    return a_dict(p)


@r.put("/procesos/{pid}")
def editar(
    pid: str, datos: ProcesoEdicion, s: Session = Depends(get_db), u: Usuario = Depends(requiere("procesos.editar"))
):
    p = obtener(s, Proceso, pid, "Proceso")
    antes = proceso_plano(p)
    verificar_version(p, datos.version)
    for k, v in datos.columnas().items():
        setattr(p, k, v)
    _poner_solicitudes(p, datos.solicitudes_penales)
    Auto.normalizar_proceso(p, date.today(), datos.crear_medidas)
    p.actualizado_por = u.id
    s.flush()
    auditoria.registrar(s, u, "proceso", p.id, auditoria.EDITAR, antes=antes, despues=proceso_plano(p))
    # al editar no se vuelve a crear la actuación inicial; sí se actualiza la gestión de garantías
    _aplicar_automatismos(s, u, p, nuevo=False, crear_inicial=False)
    s.commit()
    return _detalle(s, p, u)


@r.put("/procesos/{pid}/notas")
def editar_notas(pid: str, datos: NotasIn, s: Session = Depends(get_db), u=Depends(requiere("procesos.notas"))):
    return _editar_proceso(s, u, pid, {"notas": datos.notas}, datos.version)


@r.delete("/procesos/{pid}", status_code=204)
def eliminar(pid: str, s: Session = Depends(get_db), u: Usuario = Depends(requiere("procesos.eliminar"))):
    p = obtener(s, Proceso, pid, "Proceso")
    antes = a_dict(p) | {"actuaciones": [a_dict(a) for a in p.actuaciones]}
    auditoria.registrar(s, u, "proceso", p.id, auditoria.ELIMINAR, antes=antes)
    s.delete(p)
    s.commit()


# ---------- actuaciones ----------


def _act_completa(s: Session, a: Actuacion) -> dict:
    hermanas = list(s.scalars(select(Actuacion).where(Actuacion.proceso_id == a.proceso_id)))
    return act_dict(a, construir_contexto(s), hermanas, mapa_rutas(s))


@r.post("/actuaciones/derivar")
def derivar(datos: ActuacionBase, s: Session = Depends(get_db), _=Depends(usuario_actual)):
    """Vista previa de cómo quedaría clasificada una actuación sin guardarla, con lo que se llenaría solo."""
    ctx = construir_contexto(s)
    a = Actuacion(**datos.model_dump())
    Sec.autocompletar_actuacion(a, ctx.calendario)
    return derivado_act(a, ctx) | {
        "autocompletado": {
            "constancia": iso(a.constancia),
            "pase": iso(a.pase),
            "ejecutoria": iso(a.ejecutoria),
            "cumplida": iso(a.cumplida),
        }
    }


@r.post("/procesos/{pid}/actuaciones", status_code=201)
def crear_actuacion(
    pid: str, datos: ActuacionIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("actuaciones.crear"))
):
    obtener(s, Proceso, pid, "Proceso")
    a = Actuacion(**datos.model_dump(), proceso_id=pid, creado_por=u.id, actualizado_por=u.id)
    Sec.autocompletar_actuacion(a, construir_contexto(s).calendario)
    s.add(a)
    s.flush()
    auditoria.registrar(s, u, "actuacion", a.id, auditoria.CREAR, despues=a_dict(a))
    s.commit()
    return _act_completa(s, a)


@r.put("/actuaciones/{aid}")
def editar_actuacion(
    aid: str, datos: ActuacionEdicion, s: Session = Depends(get_db), u: Usuario = Depends(requiere("actuaciones.editar"))
):
    a = obtener(s, Actuacion, aid, "Actuación")
    antes = a_dict(a)
    verificar_version(a, datos.version)
    for k, v in datos.model_dump(exclude={"version"}).items():
        setattr(a, k, v)
    Sec.autocompletar_actuacion(a, construir_contexto(s).calendario)
    a.actualizado_por = u.id
    s.flush()
    auditoria.registrar(s, u, "actuacion", a.id, auditoria.EDITAR, antes=antes, despues=a_dict(a))
    s.commit()
    return _act_completa(s, a)


@r.delete("/actuaciones/{aid}", status_code=204)
def eliminar_actuacion(aid: str, s: Session = Depends(get_db), u: Usuario = Depends(requiere("actuaciones.eliminar"))):
    a = obtener(s, Actuacion, aid, "Actuación")
    auditoria.registrar(s, u, "actuacion", a.id, auditoria.ELIMINAR, antes=a_dict(a))
    s.delete(a)
    s.commit()


# ---------- tablero ----------


@r.get("/tablero")
def tablero(s: Session = Depends(get_db), u: Usuario = Depends(requiere("procesos.ver"))):
    ctx = construir_contexto(s)
    procesos, acts = _todo(s)
    radicados = {p.id: p.radicado for p in procesos}
    st = E.global_stats([a for lista in acts.values() for a in lista], ctx)
    st["proximos"] = [
        {
            "proceso_id": a.proceso_id,
            "radicado": radicados.get(a.proceso_id, "?"),
            "descripcion": desc,
            "fecha": iso(f),
            "faltan": (f - ctx.hoy).days,
        }
        for f, a, desc in st["proximos"][:10]
    ]
    st["por_situacion"] = [
        {"codigo": c, "situacion": E.SIT[c], "badge": E.SIT_BADGE[c], "total": n}
        for c, n in enumerate(st["por_situacion"])
    ]
    st["procesos"] = len(procesos)
    st["hoy"] = iso(ctx.hoy)
    if "audiencias.ver" in permisos_de(u):
        todas = [a for lista in acts.values() for a in lista]
        st["audiencias_pendientes"] = len(Aud.pendientes(todas, ctx.hoy))
    return st


# ---------- gestión por paquetes ----------


def _paquete(
    s: Session, materia: str, situacion: int | None, tipo: str, q: str, desde: date | None = None, hasta: date | None = None
):
    ctx = construir_contexto(s)
    procesos = {p.id: p for p in s.scalars(select(Proceso))}
    vivas = []
    for a in s.scalars(select(Actuacion)):
        c = E.codigo(a, ctx)
        if E.viva(c):
            vivas.append((a, c))
    conteo: dict[str, int] = defaultdict(int)
    for a, _ in vivas:
        conteo[a.materia or "Otro"] += 1
    q = q.lower().strip()
    filas = []
    for a, c in vivas:
        p = procesos[a.proceso_id]
        if materia and (a.materia or "Otro") != materia:
            continue
        if situacion is not None and c != situacion:
            continue
        if tipo and a.tipo_solicitud != tipo:
            continue
        if desde or hasta:
            f = E.fecha_activa(a, ctx) or a.fecha_memorial
            if not f or (desde and f < desde) or (hasta and f > hasta):
                continue
        if q and q not in " ".join([p.radicado, a.descripcion, _partes(p), a.materia, a.tipo_solicitud, a.cuaderno]).lower():
            continue
        filas.append((a, p))
    # sin fecha que la active, al final
    filas.sort(key=lambda x: E.fecha_activa(x[0], ctx) or date.max)
    return ctx, len(vivas), conteo, filas


@r.get("/paquetes")
def paquetes(
    materia: str = "",
    situacion: int | None = None,
    tipo: str = "",
    q: str = "",
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("paquetes.ver")),
):
    ctx, total, conteo, filas = _paquete(s, materia, situacion, tipo, q, desde, hasta)
    return {
        "total": total,
        "materias": conteo,
        "filas": [act_dict(a, ctx) | {"radicado": p.radicado, "partes": _partes(p)} for a, p in filas],
    }


@r.get("/paquetes.csv")
def paquetes_csv(
    materia: str = "",
    situacion: int | None = None,
    tipo: str = "",
    q: str = "",
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("paquetes.exportar")),
):
    ctx, _total, _conteo, filas = _paquete(s, materia, situacion, tipo, q, desde, hasta)
    lineas = ["Radicado;Partes;Cuaderno;Materia;Tipo de solicitud;Descripción;Situación;Término;Vencimiento"]
    for a, p in filas:
        celdas = [
            p.radicado, _partes(p), a.cuaderno, a.materia, a.tipo_solicitud, a.descripcion,
            E.SIT[E.codigo(a, ctx)], a.termino, _fmt(E.vencimiento(a, ctx)),
        ]  # fmt: skip
        lineas.append(";".join('"' + str(c or "").replace('"', '""') + '"' for c in celdas))
    # BOM para que Excel abra las tildes bien
    return Response("﻿" + "\n".join(lineas) + "\n", media_type="text/csv; charset=utf-8")
