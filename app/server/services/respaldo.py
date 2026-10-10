"""Respaldo y restauración en JSON. Acepta el formato propio y el que exporta el HTML original."""

import base64
import json
import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy, stat_evento_desde_legacy
from app.server.db.models import (
    Actuacion,
    CalDia,
    CalSuspension,
    Catalogo,
    Config,
    Festivo,
    Firmante,
    Personal,
    Plantilla,
    Proceso,
    Rol,
    RolPermiso,
    Ruta,
    RutaPaso,
    Sesion,
    SolicitudPenal,
    StatEvento,
    Termino,
    TipoRuta,
    Usuario,
)
from app.server.db.seeds import CATALOGOS
from app.server.services.documentos import data_uri
from app.server.services.ejemplos import vaciar
from app.server.services.serial import a_dict
from app.server.services.sierju import completar_tipos_sierju

FORMATO = "control-procesos"
VERSION = 4
CLAVES_JUZGADO = ("juzgado", "ciudad", "prefijo")
MEMBRETE = "membrete"
PREFIJO_AUTO = "respaldo_auto"
PREFIJO_PREVIO = "pre-restauracion"
NOMBRE_VALIDO = re.compile(r"^[\w.-]+\.json$")

# claves del HTML original -> tipo de catálogo
_CATALOGOS_LEGACY = {
    "materias": ("materias",),
    "tipos_solicitud": ("tiposSolicitud",),
    "cuadernos": ("cuadernos",),
    "macroetapas": ("macroetapas",),
    "asuntos_civil": ("asuntos", "civil"),
    "asuntos_familia": ("asuntos", "familia"),
    "cargos": ("roles",),
}
_PASO = ("nombre", "materia", "origen", "termino", "descripcion")
_PASO_AUD = ("es_audiencia", "aud_estado")


class RespaldoInvalido(ValueError):
    pass


# ---------- exportar ----------


def exportar(s: Session) -> dict:
    usuarios = {u.id: u.usuario for u in s.scalars(select(Usuario))}

    def con_autores(obj, *campos: str) -> dict:
        d = a_dict(obj)
        for campo in campos or ("creado_por", "actualizado_por"):
            d[campo] = usuarios.get(getattr(obj, campo))
        return d

    def proceso(p: Proceso) -> dict:
        d = con_autores(p)
        d["solicitudes_penales"] = [_sin(a_dict(x), "proceso_id") for x in p.solicitudes_penales]
        return d

    cfg = {c.clave: c for c in s.scalars(select(Config))}
    membrete = cfg.get(MEMBRETE)
    catalogos: dict[str, list[str]] = {tipo: [] for tipo in CATALOGOS}
    for c in s.scalars(select(Catalogo).order_by(Catalogo.orden, Catalogo.id)):
        catalogos.setdefault(c.tipo, []).append(c.valor)
    dias = s.execute(select(CalDia.fecha, CalDia.tipo).order_by(CalDia.fecha)).all()
    return {
        "formato": FORMATO,
        "version": VERSION,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "procesos": [proceso(p) for p in s.scalars(select(Proceso).order_by(Proceso.creado_en))],
        "actuaciones": [con_autores(a) for a in s.scalars(select(Actuacion).order_by(Actuacion.creado_en))],
        "stat_eventos": [
            con_autores(e, "creado_por") for e in s.scalars(select(StatEvento).order_by(StatEvento.fecha, StatEvento.creado_en))
        ],
        "config": {
            "juzgado": {k: cfg[k].valor if k in cfg else "" for k in CLAVES_JUZGADO},
            "membrete": data_uri(membrete.binario, membrete.valor) if membrete and membrete.binario else None,
            "catalogos": catalogos,
            "terminos": [
                {k: getattr(t, k) for k in ("nombre", "dias", "habil", "responsable", "categoria")}
                for t in s.scalars(select(Termino).order_by(Termino.orden, Termino.id))
            ],
            "rutas": [
                {
                    "id": r.id,
                    "nombre": r.nombre,
                    "descripcion": r.descripcion,
                    "pasos": [{k: getattr(p, k) for k in _PASO + _PASO_AUD} for p in r.pasos],
                }
                for r in s.scalars(select(Ruta).order_by(Ruta.orden))
            ],
            "tipo_ruta": dict(s.execute(select(TipoRuta.tipo_solicitud, TipoRuta.ruta_id)).all()),
            "calendario": {
                "festivos": [f.isoformat() for f in s.scalars(select(Festivo.fecha).order_by(Festivo.fecha))],
                "suspensiones": [
                    {"desde": x.desde.isoformat(), "hasta": x.hasta.isoformat(), "motivo": x.motivo}
                    for x in s.scalars(select(CalSuspension).order_by(CalSuspension.desde))
                ],
                "cerrados": [f.isoformat() for f, t in dias if t == CalDia.CERRADO],
                "reabiertos": [f.isoformat() for f, t in dias if t == CalDia.REABIERTO],
            },
            "firmantes": [
                {
                    "id": f.id,
                    "nombre": f.nombre,
                    "cargo": f.cargo,
                    "firma": data_uri(f.firma, f.firma_mime) if f.firma else None,
                }
                for f in s.scalars(select(Firmante).order_by(Firmante.orden, Firmante.nombre))
            ],
            "personal": [a_dict(x) for x in s.scalars(select(Personal).order_by(Personal.nombre))],
        },
        "plantillas": [a_dict(p) for p in s.scalars(select(Plantilla).order_by(Plantilla.tipo, Plantilla.nombre))],
        "roles": [
            {
                "nombre": r.nombre,
                "descripcion": r.descripcion,
                "es_sistema": r.es_sistema,
                "permisos": sorted(p.permiso for p in r.permisos),
            }
            for r in s.scalars(select(Rol).order_by(Rol.id))
        ],
        # los hash de contraseña van incluidos para poder restaurar los accesos; el archivo debe guardarse con cuidado
        "usuarios": [
            {
                "usuario": u.usuario,
                "nombre": u.nombre,
                "password_hash": u.password_hash,
                "rol": u.rol.nombre,
                "activo": u.activo,
                "preferencias": u.preferencias or {},
            }
            for u in s.scalars(select(Usuario).order_by(Usuario.id))
        ],
    }


def _sin(d: dict, *claves: str) -> dict:
    for k in claves:
        d.pop(k, None)
    return d


# ---------- leer ----------


def _proceso_legacy(d: dict) -> dict:
    p = proceso_desde_legacy(d)
    out = a_dict(p)
    out["solicitudes_penales"] = [_sin(a_dict(x), "proceso_id") for x in p.solicitudes_penales]
    return out


def _paso_legacy(p: dict) -> dict:
    return {**{k: p.get(k) or "" for k in _PASO}, "es_audiencia": bool(p.get("esAudiencia")), "aud_estado": p.get("audEstado") or ""}


def _de_legacy(d: dict) -> dict:
    """Convierte la exportación del HTML original (v1 o v2) al formato propio."""
    out = {
        "formato": "legacy",
        "procesos": [_proceso_legacy(p) for p in d["procesos"]],
        "actuaciones": [a_dict(actuacion_desde_legacy(a)) for a in d["actuaciones"]],
    }
    if isinstance(d.get("statEventos"), list):
        out["stat_eventos"] = [a_dict(stat_evento_desde_legacy(e)) for e in d["statEventos"] if isinstance(e, dict) and e.get("fecha")]
    if isinstance(d.get("plantillas"), list):
        out["plantillas"] = d["plantillas"]
    c = d.get("config")
    if not isinstance(c, dict):
        return out
    cfg: dict = {"juzgado": {k: c.get(k) or "" for k in CLAVES_JUZGADO}}
    if "escudo" in c:
        cfg["membrete"] = c["escudo"] or None
    catalogos = {}
    for tipo, ruta in _CATALOGOS_LEGACY.items():
        valores = c
        for clave in ruta:
            valores = valores.get(clave) if isinstance(valores, dict) else None
        if isinstance(valores, list):
            catalogos[tipo] = valores
    if catalogos:
        cfg["catalogos"] = catalogos
    if isinstance(c.get("terminos"), list):
        cfg["terminos"] = [
            {
                "nombre": t.get("n"),
                "dias": t.get("d"),
                "habil": t.get("h") is not False,
                "responsable": t.get("r") or "",
                "categoria": t.get("c") or "",
            }
            for t in c["terminos"]
        ]
    if isinstance(c.get("rutas"), list):
        cfg["rutas"] = [
            {
                "id": r.get("id"),
                "nombre": r.get("nombre"),
                "descripcion": r.get("desc") or "",
                "pasos": [_paso_legacy(p) for p in r.get("pasos") or []],
            }
            for r in c["rutas"]
        ]
        cfg["tipo_ruta"] = c.get("tipoRuta") or {}
    if isinstance(c.get("calendario"), dict):
        cfg["calendario"] = {k: c["calendario"].get(k) or [] for k in ("suspensiones", "cerrados", "reabiertos")}
    if isinstance(c.get("firmantes"), list):
        cfg["firmantes"] = c["firmantes"]
    if isinstance(c.get("personal"), list):
        cfg["personal"] = [
            {"id": x.get("id"), "nombre": x.get("nombre"), "cargo": x.get("rol") or "", "activo": True}
            for x in c["personal"]
            if isinstance(x, dict)
        ]
    out["config"] = cfg
    return out


def normalizar(datos) -> dict:
    if not isinstance(datos, dict) or not isinstance(datos.get("procesos"), list) or not isinstance(datos.get("actuaciones"), list):
        raise RespaldoInvalido("El archivo no es un respaldo de Control de Procesos")
    try:
        if datos.get("formato") == FORMATO:
            if not isinstance(datos.get("version"), int) or datos["version"] > VERSION:
                raise RespaldoInvalido("El respaldo fue creado con una versión más nueva del programa")
            return datos
        if "formato" in datos:
            raise RespaldoInvalido("Formato de respaldo desconocido")
        return _de_legacy(datos)
    except (KeyError, TypeError, AttributeError, ValueError) as e:
        if isinstance(e, RespaldoInvalido):
            raise
        raise RespaldoInvalido(f"El respaldo tiene datos mal formados ({e})") from e


def _binario(uri) -> tuple[bytes | None, str]:
    if not uri:
        return None, ""
    m = re.match(r"^data:([\w/+.-]+);base64,(.+)$", uri, re.S)
    if not m:
        raise RespaldoInvalido("Imagen mal formada en el respaldo")
    return base64.b64decode(m.group(2)), m.group(1)


def _modelo(modelo, d: dict, **extra):
    """Crea el modelo a partir de un dict con los nombres de columna; ignora lo desconocido y lo vacío."""
    kw = {}
    for col in modelo.__table__.columns:
        v = extra[col.name] if col.name in extra else d.get(col.name)
        if v is None:
            continue
        tipo = col.type.python_type
        if tipo is date:
            v = date.fromisoformat(v)
        elif tipo is datetime:
            v = datetime.fromisoformat(v)
        elif tipo is bytes:
            continue
        kw[col.name] = v
    return modelo(**kw)


# ---------- restaurar ----------


def _restaurar_usuarios(s: Session, n: dict) -> int:
    roles, usuarios = n["roles"], n["usuarios"]
    admins = {r["nombre"] for r in roles if r.get("es_sistema")}
    if not any(u.get("activo") and u.get("rol") in admins for u in usuarios):
        raise RespaldoInvalido("El respaldo no trae ningún administrador activo; no se restauran los usuarios")
    for tabla in (Sesion, Usuario, RolPermiso, Rol):
        s.execute(delete(tabla))
    por_nombre = {}
    for r in roles:
        rol = Rol(nombre=r["nombre"], descripcion=r.get("descripcion") or "", es_sistema=bool(r.get("es_sistema")))
        rol.permisos = [RolPermiso(permiso=p) for p in dict.fromkeys(r.get("permisos") or [])]
        por_nombre[rol.nombre] = rol
        s.add(rol)
    for u in usuarios:
        s.add(
            Usuario(
                usuario=u["usuario"],
                nombre=u.get("nombre") or u["usuario"],
                password_hash=u["password_hash"],
                rol=por_nombre[u["rol"]],
                activo=bool(u.get("activo")),
                preferencias=u.get("preferencias") or {},
            )
        )
    s.flush()
    return len(usuarios)


def _restaurar_config(s: Session, cfg: dict, plantillas) -> None:
    if "juzgado" in cfg:
        for clave in CLAVES_JUZGADO:
            s.merge(Config(clave=clave, valor=cfg["juzgado"].get(clave) or ""))
    if MEMBRETE in cfg:
        contenido, mime = _binario(cfg[MEMBRETE])
        s.merge(Config(clave=MEMBRETE, valor=mime, binario=contenido))
    for tipo, valores in (cfg.get("catalogos") or {}).items():
        if tipo not in CATALOGOS:
            continue
        s.execute(delete(Catalogo).where(Catalogo.tipo == tipo))
        s.add_all(Catalogo(tipo=tipo, valor=v, orden=i) for i, v in enumerate(dict.fromkeys(x for x in valores if x)))
    if "terminos" in cfg:
        s.execute(delete(Termino))
        unicos: dict[str, dict] = {}
        for t in cfg["terminos"]:
            if t.get("nombre") and t.get("dias"):
                unicos.setdefault(t["nombre"], t)
        s.add_all(
            Termino(
                nombre=t["nombre"],
                dias=int(t["dias"]),
                habil=t.get("habil") is not False,
                responsable=t.get("responsable") or "",
                categoria=t.get("categoria") or "",
                orden=i,
            )
            for i, t in enumerate(unicos.values())
        )
    if "rutas" in cfg:
        for tabla in (TipoRuta, RutaPaso, Ruta):
            s.execute(delete(tabla))
        ids = set()
        for i, r in enumerate(cfg["rutas"]):
            if not r.get("id") or r["id"] in ids:
                continue
            ids.add(r["id"])
            pasos = [
                RutaPaso(
                    orden=j,
                    nombre=p.get("nombre") or f"Paso {j + 1}",
                    es_audiencia=bool(p.get("es_audiencia")),
                    aud_estado=p.get("aud_estado") or "",
                    **{k: p.get(k) or "" for k in _PASO[1:]},
                )
                for j, p in enumerate(r.get("pasos") or [])
            ]
            s.add(Ruta(id=r["id"], nombre=r.get("nombre") or r["id"], descripcion=r.get("descripcion") or "", orden=i, pasos=pasos))
        s.flush()
        s.add_all(TipoRuta(tipo_solicitud=t, ruta_id=rid) for t, rid in (cfg.get("tipo_ruta") or {}).items() if rid in ids)
    cal = cfg.get("calendario")
    if cal is not None:
        if "festivos" in cal:
            s.execute(delete(Festivo))
            s.add_all(Festivo(fecha=date.fromisoformat(f)) for f in dict.fromkeys(cal["festivos"]))
        s.execute(delete(CalSuspension))
        s.execute(delete(CalDia))
        s.add_all(
            CalSuspension(desde=date.fromisoformat(x["desde"]), hasta=date.fromisoformat(x["hasta"]), motivo=x.get("motivo") or "")
            for x in cal.get("suspensiones") or []
        )
        for tipo, clave in ((CalDia.CERRADO, "cerrados"), (CalDia.REABIERTO, "reabiertos")):
            s.add_all(CalDia(fecha=date.fromisoformat(f), tipo=tipo) for f in dict.fromkeys(cal.get(clave) or []))
    if "firmantes" in cfg:
        s.execute(delete(Firmante))
        for i, f in enumerate(cfg["firmantes"]):
            firma, mime = _binario(f.get("firma"))
            extra = {"id": f["id"]} if f.get("id") else {}
            s.add(Firmante(nombre=f.get("nombre") or "", cargo=f.get("cargo") or "", firma=firma, firma_mime=mime, orden=i, **extra))
    if "personal" in cfg:
        s.execute(delete(Personal))
        ids = set()
        for x in cfg["personal"]:
            if not x.get("nombre") or (x.get("id") and x["id"] in ids):
                continue
            ids.add(x.get("id"))
            s.add(_modelo(Personal, x))
    if plantillas is not None:
        s.execute(delete(Plantilla))
        s.add_all(_modelo(Plantilla, p) for p in plantillas if p.get("nombre") and p.get("tipo"))


def restaurar(s: Session, datos, incluir_usuarios: bool = False) -> dict:
    """Reemplaza los datos por los del respaldo. No hace commit: si algo falla, quien llama revierte todo."""
    n = normalizar(datos)
    # los objetos ya cargados en la sesión chocarían con los que se van a insertar con el mismo id
    s.expunge_all()
    try:
        usuarios = 0
        if incluir_usuarios and n.get("usuarios") and n.get("roles"):
            usuarios = _restaurar_usuarios(s, n)
        _restaurar_config(s, n.get("config") or {}, n.get("plantillas"))
        ids_usuario = {u: i for u, i in s.execute(select(Usuario.usuario, Usuario.id))}

        def autores(d: dict) -> dict:
            return {k: ids_usuario.get(d.get(k)) for k in ("creado_por", "actualizado_por")}

        vaciar(s)
        ids = set()
        for p in n["procesos"]:
            if not p.get("id") or p["id"] in ids:
                raise RespaldoInvalido("Hay procesos sin identificador o repetidos")
            ids.add(p["id"])
            proceso = _modelo(Proceso, p, **autores(p))
            proceso.solicitudes_penales = [
                _modelo(SolicitudPenal, {**x, "orden": i}, proceso_id=p["id"]) for i, x in enumerate(p.get("solicitudes_penales") or [])
            ]
            s.add(proceso)
        s.flush()
        omitidas = 0
        for a in n["actuaciones"]:
            if a.get("proceso_id") not in ids:
                omitidas += 1
                continue
            s.add(_modelo(Actuacion, a, **autores(a)))
        eventos = 0
        for e in n.get("stat_eventos") or []:
            if not e.get("fecha") or not e.get("seccion"):
                continue
            # un evento manual sobrevive aunque su proceso no venga en el respaldo
            enlace = e.get("proceso_id") if e.get("proceso_id") in ids else None
            s.add(_modelo(StatEvento, e, proceso_id=enlace, creado_por=ids_usuario.get(e.get("creado_por"))))
            eventos += 1
        s.flush()
        if n["formato"] != FORMATO or n["version"] < 4:
            # el campo no existía: se sugiere como hacía la v2 al abrir datos viejos
            completar_tipos_sierju(s)
    except RespaldoInvalido:
        raise
    except Exception as e:  # dato mal formado o que viola una restricción de la base
        raise RespaldoInvalido(f"No se pudo restaurar: el respaldo tiene datos mal formados ({type(e).__name__})") from e
    return {
        "formato": n["formato"],
        "procesos": len(ids),
        "actuaciones": len(n["actuaciones"]) - omitidas,
        "actuaciones_omitidas": omitidas,
        "stat_eventos": eventos,
        "usuarios_restaurados": usuarios,
    }


# ---------- archivos ----------


def guardar_archivo(directorio: Path, prefijo: str, datos: dict, momento: datetime | None = None) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / f"{prefijo}_{(momento or datetime.now()).strftime('%Y-%m-%d_%H%M%S')}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return ruta


def listar_archivos(directorio: Path) -> list[Path]:
    if not directorio.is_dir():
        return []
    return sorted((p for p in directorio.glob("*.json") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def rotar(directorio: Path, prefijo: str, conservar: int) -> None:
    propios = sorted(p for p in directorio.glob(f"{prefijo}_*.json"))
    for viejo in propios[: max(0, len(propios) - conservar)]:
        viejo.unlink()


def ruta_segura(directorio: Path, nombre: str) -> Path | None:
    if not NOMBRE_VALIDO.match(nombre):
        return None
    ruta = directorio / nombre
    return ruta if ruta.is_file() and ruta.resolve().parent == directorio.resolve() else None
