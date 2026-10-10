from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, obtener, requiere, usuario_actual
from app.server.api.esquemas import (
    DiaIn,
    FestivoIn,
    FirmanteIn,
    JuzgadoIn,
    PasoIn,
    PersonalIn,
    PlantillaIn,
    RutaIn,
    SuspensionIn,
    TerminoIn,
    TipoRutaIn,
    ValorIn,
)
from app.server.db.models import (
    CalDia,
    CalSuspension,
    Catalogo,
    Config,
    Festivo,
    Firmante,
    Personal,
    Plantilla,
    Ruta,
    RutaPaso,
    Termino,
    TipoRuta,
    Usuario,
)
from app.server.db.seeds import CATALOGOS, cargar_catalogos, cargar_sierju
from app.server.domain import audiencias as Aud
from app.server.domain import automatismos as Auto
from app.server.domain import estados as E
from app.server.domain import naturaleza as N
from app.server.domain import secretaria as Sec
from app.server.domain.calendario import es_habil
from app.server.services import auditoria
from app.server.services.contexto import construir_calendario, mapa_rutas
from app.server.services.serial import a_dict, paso_dict

r = APIRouter(prefix="/api/config", tags=["configuración"])

CLAVES_JUZGADO = ("juzgado", "ciudad", "prefijo")
MEMBRETE = "membrete"
MAX_IMAGEN = 2 * 1024 * 1024

# atajos de color de la v2: un clic deja el tema institucional listo
PALETAS = (
    ("#1f3864", "Azul institucional"),
    ("#0f6e4f", "Verde"),
    ("#7a1f2b", "Vinotinto"),
    ("#334155", "Gris pizarra"),
    ("#0e7490", "Teal"),
    ("#5b21b6", "Púrpura"),
)


def _guardar(s: Session, u: Usuario, entidad: str, obj, accion: str, antes=None) -> dict:
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "Ya existe un registro con ese nombre o valor") from None
    d = a_dict(obj)
    clave = d.get("id") or d.get("fecha") or d.get("tipo_solicitud") or d.get("clave")
    auditoria.registrar(s, u, entidad, clave, accion, antes=antes, despues=d)
    s.commit()
    return d


def _eliminar(s: Session, u: Usuario, entidad: str, obj) -> None:
    d = a_dict(obj)
    clave = d.get("id") or d.get("fecha") or d.get("tipo_solicitud")
    auditoria.registrar(s, u, entidad, clave, auditoria.ELIMINAR, antes=d)
    s.delete(obj)
    s.commit()


def _siguiente_orden(s: Session, columna, *filtros) -> int:
    return (s.scalar(select(func.max(columna)).where(*filtros)) or 0) + 1


async def _imagen(request: Request) -> tuple[bytes, str]:
    mime = (request.headers.get("content-type") or "").split(";")[0].strip()
    if not mime.startswith("image/"):
        raise HTTPException(415, "El archivo debe ser una imagen")
    contenido = await request.body()
    if not contenido or len(contenido) > MAX_IMAGEN:
        raise HTTPException(413, "La imagen está vacía o supera los 2 MB")
    return contenido, mime


def firmante_dict(f: Firmante) -> dict:
    return {"id": f.id, "nombre": f.nombre, "cargo": f.cargo, "tiene_firma": bool(f.firma), "orden": f.orden}


def ruta_dict(ruta: Ruta) -> dict:
    return {
        "id": ruta.id,
        "nombre": ruta.nombre,
        "descripcion": ruta.descripcion,
        "pasos": [paso_dict(p) for p in ruta.pasos],
    }


# ---------- lectura ----------


@r.get("")
def leer(s: Session = Depends(get_db), _=Depends(usuario_actual)):
    """Todo lo que el frontend necesita para armar formularios y pantallas de configuración."""
    semilla = cargar_catalogos()
    catalogos = {tipo: [] for tipo in CATALOGOS}
    for c in s.scalars(select(Catalogo).order_by(Catalogo.orden, Catalogo.id)):
        catalogos.setdefault(c.tipo, []).append({"id": c.id, "valor": c.valor})
    dias = s.execute(select(CalDia.fecha, CalDia.tipo).order_by(CalDia.fecha)).all()
    cfg = {c.clave: c for c in s.scalars(select(Config))}
    return {
        "catalogos": catalogos,
        "terminos": [a_dict(t) for t in s.scalars(select(Termino).order_by(Termino.orden, Termino.id))],
        "rutas": [ruta_dict(x) for x in mapa_rutas(s).values()],
        "tipo_ruta": dict(s.execute(select(TipoRuta.tipo_solicitud, TipoRuta.ruta_id)).all()),
        "calendario": {
            "festivos": [f.isoformat() for f in s.scalars(select(Festivo.fecha).order_by(Festivo.fecha))],
            "suspensiones": [a_dict(x) for x in s.scalars(select(CalSuspension).order_by(CalSuspension.desde))],
            "cerrados": [f.isoformat() for f, t in dias if t == CalDia.CERRADO],
            "reabiertos": [f.isoformat() for f, t in dias if t == CalDia.REABIERTO],
        },
        "plantillas": [a_dict(p) for p in s.scalars(select(Plantilla).order_by(Plantilla.tipo.desc(), Plantilla.nombre))],
        "firmantes": [firmante_dict(f) for f in s.scalars(select(Firmante).order_by(Firmante.orden, Firmante.nombre))],
        "juzgado": {k: cfg[k].valor if k in cfg else "" for k in CLAVES_JUZGADO},
        "tiene_membrete": bool(MEMBRETE in cfg and cfg[MEMBRETE].binario),
        "sugerencias_termino": semilla["sugerencias"],
        "motivos_pase": semilla["motivosPase"],
        "situaciones": [{"codigo": c, "situacion": t, "badge": E.SIT_BADGE[c]} for c, t in enumerate(E.SIT)],
        # --- v2 ---
        # las listas que dependen de la naturaleza no van aquí (son miles de delitos): se piden a /naturaleza
        "naturalezas": list(N.NATURALEZAS),
        "areas": list(N.AREAS),
        "leyes_penales": list(N.LEYES_PENALES),
        "procedimientos_penales": [N.GARANTIAS, N.CONOCIMIENTO],
        "personal": [a_dict(x) for x in s.scalars(select(Personal).order_by(Personal.nombre))],
        "modos_cierre": list(Sec.MODOS_CIERRE),
        "solicitud_penal": {
            "entradas": ["Nueva solicitud", "Reingreso"],
            "detalles_no_efectiva": list(Auto.DETALLES_SALIDA_NO_EFECTIVA),
        },
        "actuacion": {
            "tipos_providencia": list(Sec.TIPOS_PROVIDENCIA),
            "tramites_posteriores": list(Sec.TRAMITES_POSTERIORES),
            "recursos": list(Sec.RECURSOS),
            "objetos_recurso": list(Sec.OBJETOS_RECURSO),
            "resultados_superior": list(Sec.RESULTADOS_SUPERIOR),
            "notif_formas": list(Sec.NOTIF_FORMAS),
            "si_no": list(Sec.SI_NO),
            "ejec_dias": Sec.EJEC_DIAS,
        },
        "audiencias": {
            "estados": list(Aud.ESTADOS),
            "materia": Aud.MATERIA,
            "causas": {k: list(v) for k, v in cargar_sierju()["audiencias"]["columnas_causa"].items()},
        },
        "paletas": [list(x) for x in PALETAS],
    }


@r.get("/naturaleza")
def listas_de_naturaleza(naturaleza: str = "", clase: str = "", s: Session = Depends(get_db), _=Depends(usuario_actual)):
    """Todo lo que cambia al elegir la naturaleza. El frontend lo pide y lo guarda en caché."""
    catalogo = [c.valor for c in s.scalars(select(Catalogo).where(Catalogo.tipo == "tipos_solicitud").order_by(Catalogo.orden, Catalogo.id))]
    return {
        "naturaleza": naturaleza,
        "area": N.area_de(naturaleza),
        "sugerido": N.sug_sierju(clase, naturaleza),
        "tipo_sierju": N.lista_sierju(naturaleza),
        "salidas": N.lista_salidas(naturaleza),
        "entradas": N.entradas_sierju(naturaleza),
        "penal_solicitudes": N.penal_solicitudes(naturaleza),
        "tipos_gestion": N.tipos_gestion(naturaleza, catalogo),
        "salidas_act": N.salidas_act(naturaleza),
        "aud_tipos": Aud.tipos(naturaleza),
        "es_penal": N.es_penal(naturaleza),
        "es_garantias": N.es_garantias(naturaleza),
        "es_constitucional": N.es_constitucional(naturaleza),
        "es_desacato": N.es_desacato(naturaleza),
    }


@r.get("/delitos")
def delitos(procedimiento: str = N.GARANTIAS, _=Depends(usuario_actual)):
    """Delitos de las dos leyes penales para el procedimiento, como (delito, ley)."""
    return [{"delito": d, "ley": ley} for d, ley in N.delitos_unificados(procedimiento)]


# ---------- personal ----------


@r.get("/personal")
def listar_personal(s: Session = Depends(get_db), _=Depends(usuario_actual)):
    return [a_dict(x) for x in s.scalars(select(Personal).order_by(Personal.nombre))]


@r.post("/personal", status_code=201)
def crear_personal(datos: PersonalIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("config.personal"))):
    x = Personal(**datos.model_dump())
    s.add(x)
    return _guardar(s, u, "personal", x, auditoria.CREAR)


@r.put("/personal/{pid}")
def editar_personal(
    pid: str, datos: PersonalIn, s: Session = Depends(get_db), u: Usuario = Depends(requiere("config.personal"))
):
    x = obtener(s, Personal, pid, "Persona")
    antes = a_dict(x)
    for k, v in datos.model_dump().items():
        setattr(x, k, v)
    return _guardar(s, u, "personal", x, auditoria.EDITAR, antes)


@r.delete("/personal/{pid}", status_code=204)
def eliminar_personal(pid: str, s: Session = Depends(get_db), u: Usuario = Depends(requiere("config.personal"))):
    _eliminar(s, u, "personal", obtener(s, Personal, pid, "Persona"))


# ---------- catálogos ----------


def _tipo_valido(tipo: str) -> None:
    if tipo not in CATALOGOS:
        raise HTTPException(404, "Catálogo no encontrado")


@r.post("/catalogos/{tipo}", status_code=201)
def crear_valor(tipo: str, datos: ValorIn, s: Session = Depends(get_db), u=Depends(requiere("config.catalogos"))):
    _tipo_valido(tipo)
    c = Catalogo(tipo=tipo, valor=datos.valor, orden=_siguiente_orden(s, Catalogo.orden, Catalogo.tipo == tipo))
    s.add(c)
    return _guardar(s, u, "catalogo", c, auditoria.CREAR)


@r.put("/catalogos/{tipo}/{cid}")
def editar_valor(
    tipo: str, cid: int, datos: ValorIn, s: Session = Depends(get_db), u=Depends(requiere("config.catalogos"))
):
    c = obtener(s, Catalogo, cid, "Valor")
    if c.tipo != tipo:
        raise HTTPException(404, "Valor no encontrado")
    antes = a_dict(c)
    c.valor = datos.valor
    return _guardar(s, u, "catalogo", c, auditoria.EDITAR, antes)


@r.delete("/catalogos/{tipo}/{cid}", status_code=204)
def eliminar_valor(tipo: str, cid: int, s: Session = Depends(get_db), u=Depends(requiere("config.catalogos"))):
    c = obtener(s, Catalogo, cid, "Valor")
    if c.tipo != tipo:
        raise HTTPException(404, "Valor no encontrado")
    _eliminar(s, u, "catalogo", c)


# ---------- términos ----------


@r.post("/terminos", status_code=201)
def crear_termino(datos: TerminoIn, s: Session = Depends(get_db), u=Depends(requiere("config.terminos"))):
    t = Termino(**datos.model_dump(), orden=_siguiente_orden(s, Termino.orden))
    s.add(t)
    return _guardar(s, u, "termino", t, auditoria.CREAR)


@r.put("/terminos/{tid}")
def editar_termino(tid: int, datos: TerminoIn, s: Session = Depends(get_db), u=Depends(requiere("config.terminos"))):
    t = obtener(s, Termino, tid, "Término")
    antes = a_dict(t)
    for k, v in datos.model_dump().items():
        setattr(t, k, v)
    return _guardar(s, u, "termino", t, auditoria.EDITAR, antes)


@r.delete("/terminos/{tid}", status_code=204)
def eliminar_termino(tid: int, s: Session = Depends(get_db), u=Depends(requiere("config.terminos"))):
    _eliminar(s, u, "termino", obtener(s, Termino, tid, "Término"))


# ---------- rutas procesales ----------


@r.post("/rutas", status_code=201)
def crear_ruta(datos: RutaIn, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    ruta = Ruta(**datos.model_dump(), orden=_siguiente_orden(s, Ruta.orden))
    s.add(ruta)
    _guardar(s, u, "ruta", ruta, auditoria.CREAR)
    return ruta_dict(ruta)


@r.put("/rutas/{rid}")
def editar_ruta(rid: str, datos: RutaIn, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    ruta = obtener(s, Ruta, rid, "Ruta")
    antes = a_dict(ruta)
    ruta.nombre, ruta.descripcion = datos.nombre, datos.descripcion
    _guardar(s, u, "ruta", ruta, auditoria.EDITAR, antes)
    return ruta_dict(ruta)


@r.delete("/rutas/{rid}", status_code=204)
def eliminar_ruta(rid: str, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    _eliminar(s, u, "ruta", obtener(s, Ruta, rid, "Ruta"))


@r.post("/rutas/{rid}/pasos", status_code=201)
def crear_paso(rid: str, datos: PasoIn, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    obtener(s, Ruta, rid, "Ruta")
    orden = _siguiente_orden(s, RutaPaso.orden, RutaPaso.ruta_id == rid)
    paso = RutaPaso(**datos.model_dump(), ruta_id=rid, orden=orden)
    s.add(paso)
    return _guardar(s, u, "ruta_paso", paso, auditoria.CREAR)


@r.put("/pasos/{pid}")
def editar_paso(pid: int, datos: PasoIn, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    paso = obtener(s, RutaPaso, pid, "Paso")
    antes = a_dict(paso)
    for k, v in datos.model_dump().items():
        setattr(paso, k, v)
    return _guardar(s, u, "ruta_paso", paso, auditoria.EDITAR, antes)


@r.delete("/pasos/{pid}", status_code=204)
def eliminar_paso(pid: int, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    _eliminar(s, u, "ruta_paso", obtener(s, RutaPaso, pid, "Paso"))


@r.put("/tipo-ruta")
def asociar_tipo_ruta(datos: TipoRutaIn, s: Session = Depends(get_db), u=Depends(requiere("config.rutas"))):
    actual = s.get(TipoRuta, datos.tipo_solicitud)
    antes = a_dict(actual) if actual else None
    if not datos.ruta_id:
        if actual:
            _eliminar(s, u, "tipo_ruta", actual)
        return {"tipo_solicitud": datos.tipo_solicitud, "ruta_id": None}
    obtener(s, Ruta, datos.ruta_id, "Ruta")
    if actual:
        actual.ruta_id = datos.ruta_id
    else:
        actual = TipoRuta(tipo_solicitud=datos.tipo_solicitud, ruta_id=datos.ruta_id)
        s.add(actual)
    return _guardar(s, u, "tipo_ruta", actual, auditoria.EDITAR if antes else auditoria.CREAR, antes)


# ---------- calendario judicial ----------


@r.get("/calendario/verificar")
def verificar_dia(fecha: date, s: Session = Depends(get_db), _=Depends(usuario_actual)):
    return {"fecha": fecha.isoformat(), "habil": es_habil(fecha, construir_calendario(s))}


@r.post("/calendario/suspensiones", status_code=201)
def crear_suspension(datos: SuspensionIn, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    desde, hasta = sorted((datos.desde, datos.hasta))
    x = CalSuspension(desde=desde, hasta=hasta, motivo=datos.motivo)
    s.add(x)
    return _guardar(s, u, "cal_suspension", x, auditoria.CREAR)


@r.delete("/calendario/suspensiones/{sid}", status_code=204)
def eliminar_suspension(sid: int, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    _eliminar(s, u, "cal_suspension", obtener(s, CalSuspension, sid, "Suspensión"))


@r.post("/calendario/dias", status_code=201)
def crear_dia(datos: DiaIn, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    x = s.get(CalDia, (datos.fecha, datos.tipo))
    if x:
        return a_dict(x)
    x = CalDia(fecha=datos.fecha, tipo=datos.tipo)
    s.add(x)
    return _guardar(s, u, "cal_dia", x, auditoria.CREAR)


@r.delete("/calendario/dias/{tipo}/{fecha}", status_code=204)
def eliminar_dia(tipo: str, fecha: date, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    _eliminar(s, u, "cal_dia", obtener(s, CalDia, (fecha, tipo), "Día"))


@r.post("/calendario/festivos", status_code=201)
def crear_festivo(datos: FestivoIn, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    x = s.get(Festivo, datos.fecha)
    if x:
        return a_dict(x)
    x = Festivo(fecha=datos.fecha)
    s.add(x)
    return _guardar(s, u, "festivo", x, auditoria.CREAR)


@r.delete("/calendario/festivos/{fecha}", status_code=204)
def eliminar_festivo(fecha: date, s: Session = Depends(get_db), u=Depends(requiere("config.calendario"))):
    _eliminar(s, u, "festivo", obtener(s, Festivo, fecha, "Festivo"))


# ---------- plantillas y firmantes ----------


@r.post("/plantillas", status_code=201)
def crear_plantilla(datos: PlantillaIn, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))):
    p = Plantilla(**datos.model_dump())
    s.add(p)
    return _guardar(s, u, "plantilla", p, auditoria.CREAR)


@r.put("/plantillas/{pid}")
def editar_plantilla(
    pid: str, datos: PlantillaIn, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))
):
    p = obtener(s, Plantilla, pid, "Plantilla")
    antes = a_dict(p)
    for k, v in datos.model_dump().items():
        setattr(p, k, v)
    return _guardar(s, u, "plantilla", p, auditoria.EDITAR, antes)


@r.delete("/plantillas/{pid}", status_code=204)
def eliminar_plantilla(pid: str, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))):
    _eliminar(s, u, "plantilla", obtener(s, Plantilla, pid, "Plantilla"))


@r.post("/firmantes", status_code=201)
def crear_firmante(datos: FirmanteIn, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))):
    f = Firmante(**datos.model_dump(), orden=_siguiente_orden(s, Firmante.orden))
    s.add(f)
    _guardar(s, u, "firmante", f, auditoria.CREAR)
    return firmante_dict(f)


@r.put("/firmantes/{fid}")
def editar_firmante(fid: str, datos: FirmanteIn, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))):
    f = obtener(s, Firmante, fid, "Firmante")
    antes = a_dict(f)
    f.nombre, f.cargo = datos.nombre, datos.cargo
    _guardar(s, u, "firmante", f, auditoria.EDITAR, antes)
    return firmante_dict(f)


@r.delete("/firmantes/{fid}", status_code=204)
def eliminar_firmante(fid: str, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))):
    _eliminar(s, u, "firmante", obtener(s, Firmante, fid, "Firmante"))


@r.get("/firmantes/{fid}/firma")
def ver_firma(fid: str, s: Session = Depends(get_db), _=Depends(usuario_actual)):
    f = obtener(s, Firmante, fid, "Firmante")
    if not f.firma:
        raise HTTPException(404, "El firmante no tiene antefirma")
    return Response(f.firma, media_type=f.firma_mime or "image/png")


@r.put("/firmantes/{fid}/firma")
async def subir_firma(
    fid: str, request: Request, s: Session = Depends(get_db), u=Depends(requiere("config.plantillas"))
):
    f = obtener(s, Firmante, fid, "Firmante")
    antes = a_dict(f)
    f.firma, f.firma_mime = await _imagen(request)
    _guardar(s, u, "firmante", f, auditoria.EDITAR, antes)
    return firmante_dict(f)


# ---------- datos del juzgado ----------


@r.put("/juzgado")
def editar_juzgado(datos: JuzgadoIn, s: Session = Depends(get_db), u=Depends(requiere("config.juzgado"))):
    nuevos = datos.model_dump()
    antes = {}
    for clave, valor in nuevos.items():
        c = s.get(Config, clave)
        antes[clave] = c.valor if c else ""
        if c:
            c.valor = valor
        else:
            s.add(Config(clave=clave, valor=valor))
    auditoria.registrar(s, u, "juzgado", "juzgado", auditoria.EDITAR, antes=antes, despues=nuevos)
    s.commit()
    return nuevos


@r.get("/membrete")
def ver_membrete(s: Session = Depends(get_db), _=Depends(usuario_actual)):
    c = s.get(Config, MEMBRETE)
    if not c or not c.binario:
        raise HTTPException(404, "No hay membrete")
    return Response(c.binario, media_type=c.valor or "image/png")


@r.put("/membrete", status_code=204)
async def subir_membrete(request: Request, s: Session = Depends(get_db), u=Depends(requiere("config.juzgado"))):
    contenido, mime = await _imagen(request)
    c = s.get(Config, MEMBRETE)
    if c:
        c.valor, c.binario = mime, contenido
    else:
        s.add(Config(clave=MEMBRETE, valor=mime, binario=contenido))
    auditoria.registrar(s, u, "juzgado", MEMBRETE, auditoria.EDITAR, despues={"bytes": len(contenido), "mime": mime})
    s.commit()
