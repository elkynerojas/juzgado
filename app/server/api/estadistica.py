from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, obtener, requiere
from app.server.api.esquemas import StatEventoIn
from app.server.db.models import Actuacion, Proceso, StatEvento, Usuario
from app.server.domain.sierju import eventos as EV
from app.server.domain.sierju import matrices as MX
from app.server.domain.sierju.secciones import ACTIVAS, SECCIONES
from app.server.domain.sierju.texto import para_mostrar
from app.server.services import auditoria
from app.server.services import sierju_excel as XL
from app.server.services.serial import a_dict, iso

r = APIRouter(prefix="/api/estadistica", tags=["estadística"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    if not desde or not hasta or desde > hasta:
        raise HTTPException(422, "Indique un periodo válido: la fecha inicial no puede ser posterior a la final.")
    return desde, hasta


def _paquete(s: Session, desde: date, hasta: date) -> EV.Paquete:
    procesos = list(s.scalars(select(Proceso).order_by(Proceso.creado_en, Proceso.radicado)))
    actuaciones = list(s.scalars(select(Actuacion).order_by(Actuacion.creado_en)))
    manuales = list(s.scalars(select(StatEvento).order_by(StatEvento.fecha)))
    return EV.todos(procesos, actuaciones, manuales, desde, hasta)


def _matrices(s: Session, desde: date, hasta: date):
    return MX.construir(_paquete(s, desde, hasta))


def _adjunto(nombre: str) -> str:
    return f'attachment; filename="{nombre}"'


def _csv(valor) -> str:
    return '"' + str(valor or "").replace('"', '""') + '"'


@r.get("")
def resumen(
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("estadistica.ver")),
):
    """Cobertura por sección, sin las etiquetas: una sola sección tiene 266 filas."""
    desde, hasta = _periodo(desde, hasta)
    paquete = _paquete(s, desde, hasta)
    matrices = MX.construir(paquete)
    radicados = dict(s.execute(select(Proceso.id, Proceso.radicado)).all())
    manuales = [e for e in s.scalars(select(StatEvento).order_by(StatEvento.fecha)) if desde <= e.fecha <= hasta]
    return {
        "periodo": {"desde": iso(desde), "hasta": iso(hasta)},
        "kpis": {
            "secciones": len(matrices),
            "con_movimiento": sum(1 for m in matrices if m.total),
            "automaticos": paquete.automaticos,
            "manuales": paquete.manuales,
            "avisos": len(paquete.avisos),
        },
        "secciones": [
            {"code": m.seccion.code, "n": m.seccion.n, "title": m.seccion.title, "total": m.total} for m in matrices
        ],
        "avisos": [
            {
                "fecha": iso(a.fecha),
                "seccion": a.seccion,
                "title": SECCIONES[a.seccion].title if a.seccion in SECCIONES else "",
                "proceso_id": a.proceso_id,
                "radicado": radicados.get(a.proceso_id, ""),
                "nota": a.nota,
            }
            for a in paquete.avisos
        ],
        "manuales": [a_dict(e) | {"radicado": radicados.get(e.proceso_id or "", "")} for e in manuales],
    }


@r.get("/secciones")
def secciones(_=Depends(requiere("estadistica.registrar"))):
    return [{"code": x.code, "n": x.n, "title": x.title} for x in ACTIVAS]


@r.get("/secciones/{code}")
def detalle(
    code: str,
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("estadistica.ver")),
):
    """El desglose fila por columna de una sección, con las etiquetas ya limpias."""
    desde, hasta = _periodo(desde, hasta)
    if code not in SECCIONES:
        raise HTTPException(404, "Sección no encontrada")
    m = next((x for x in _matrices(s, desde, hasta) if x.seccion.code == code), None)
    if m is None:
        raise HTTPException(404, "Esa sección no hace parte del formato que llena la plantilla")
    return {
        "code": code,
        "title": m.seccion.title,
        "total": m.total,
        "detalle": [
            {"fila": para_mostrar(fila), "columna": para_mostrar(col), "cantidad": cantidad}
            for fila, columnas in m.mapa.items()
            for col, cantidad in columnas.items()
            if cantidad
        ],
    }


@r.get("/secciones/{code}/etiquetas")
def etiquetas(code: str, _=Depends(requiere("estadistica.registrar"))):
    """Filas y columnas de la sección, para el formulario de dato manual. Se piden solo al abrirlo."""
    sec = SECCIONES.get(code)
    if not sec:
        raise HTTPException(404, "Sección no encontrada")
    return {
        "code": code,
        "title": sec.title,
        "filas": [{"valor": f, "etiqueta": para_mostrar(f)} for f in sec.filas],
        "columnas": [{"valor": c, "etiqueta": para_mostrar(c)} for c in sec.columnas],
    }


@r.post("/eventos", status_code=201)
def crear_evento(
    datos: StatEventoIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("estadistica.registrar"))
):
    sec = SECCIONES.get(datos.seccion)
    if not sec or sec not in ACTIVAS:
        raise HTTPException(422, "La sección no existe o no hace parte del formato que llena la plantilla.")
    if datos.fila not in sec.filas:
        raise HTTPException(422, "La fila no pertenece a esa sección.")
    if datos.columna not in sec.columnas:
        raise HTTPException(422, "La columna no pertenece a esa sección.")
    if datos.proceso_id:
        obtener(s, Proceso, datos.proceso_id, "Proceso")
    # la columna es una clave ajena: sin proceso va nula, no vacía
    campos = datos.model_dump() | {"proceso_id": datos.proceso_id or None}
    e = StatEvento(**campos, creado_por=u.id)
    s.add(e)
    s.flush()
    auditoria.registrar(s, u, "stat_evento", e.id, auditoria.CREAR, despues=a_dict(e))
    s.commit()
    return a_dict(e)


@r.delete("/eventos/{eid}", status_code=204)
def eliminar_evento(eid: str, s: Session = Depends(get_db), u: Usuario = Depends(requiere("estadistica.registrar"))):
    e = obtener(s, StatEvento, eid, "Dato estadístico")
    auditoria.registrar(s, u, "stat_evento", e.id, auditoria.ELIMINAR, antes=a_dict(e))
    s.delete(e)
    s.commit()


@r.get("/oficial.xlsx")
def oficial(
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("estadistica.exportar")),
):
    desde, hasta = _periodo(desde, hasta)
    contenido, sin_destino = XL.llenar_plantilla(_matrices(s, desde, hasta))
    cabeceras = {"content-disposition": _adjunto(XL.nombre_archivo(desde, hasta))}
    if sin_destino:
        # si una futura plantilla vuelve a perder una columna, se reporta en vez de ocultarlo
        cabeceras["x-columnas-sin-mapa"] = ",".join(sin_destino)
    return Response(contenido, media_type=XLSX, headers=cabeceras)


@r.get("/completo.xlsx")
def completo(
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("estadistica.exportar")),
):
    desde, hasta = _periodo(desde, hasta)
    contenido = XL.libro_generico(_matrices(s, desde, hasta), desde, hasta)
    cabeceras = {"content-disposition": _adjunto(XL.nombre_generico(desde, hasta))}
    return Response(contenido, media_type=XLSX, headers=cabeceras)


@r.get("/bitacora.csv")
def bitacora(
    desde: date | None = None,
    hasta: date | None = None,
    s: Session = Depends(get_db),
    _=Depends(requiere("estadistica.exportar")),
):
    """Todos los datos que se contaron, uno por línea: sirve para auditar de dónde salió cada número."""
    desde, hasta = _periodo(desde, hasta)
    paquete = _paquete(s, desde, hasta)
    radicados = dict(s.execute(select(Proceso.id, Proceso.radicado)).all())
    lineas = ["Fecha;Sección;Fila;Columna;Cantidad;Origen;Radicado;Observación"]
    for e in paquete.eventos:
        celdas = [
            iso(e.fecha), e.seccion, para_mostrar(e.fila), para_mostrar(e.columna),
            e.cantidad, e.origen, radicados.get(e.proceso_id, ""), e.nota,
        ]  # fmt: skip
        lineas.append(";".join(_csv(c) for c in celdas))
    nombre = f"SIERJU_bitacora_{desde.isoformat()}_{hasta.isoformat()}.csv"
    # BOM para que Excel abra bien las tildes
    return Response(
        "﻿" + "\n".join(lineas) + "\n",
        media_type="text/csv; charset=utf-8",
        headers={"content-disposition": _adjunto(nombre)},
    )
