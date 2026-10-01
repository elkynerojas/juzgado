import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, permisos_de, requiere
from app.server.db.models import Usuario
from app.server.services import auditoria, programador, respaldo

r = APIRouter(prefix="/api/respaldo", tags=["respaldo"])

PERMISOS_USUARIOS = {"usuarios.gestionar", "roles.gestionar"}


class Programacion(BaseModel):
    activo: bool
    hora: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
    conservar: int = Field(ge=1, le=365)


def _dir(request: Request) -> Path:
    return request.app.state.dir_respaldos


def _descarga(datos: dict, nombre: str) -> Response:
    return Response(
        json.dumps(datos, ensure_ascii=False, indent=1),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


def _archivo(request: Request, nombre: str) -> Path:
    ruta = respaldo.ruta_segura(_dir(request), nombre)
    if not ruta:
        raise HTTPException(404, "Respaldo no encontrado")
    return ruta


def _restaurar(s: Session, u: Usuario, directorio: Path, datos, usuarios: bool) -> dict:
    if usuarios and not PERMISOS_USUARIOS <= permisos_de(u):
        raise HTTPException(403, "Para restaurar usuarios y roles debe poder gestionarlos")
    try:
        respaldo.normalizar(datos)  # se valida antes de tocar nada
        previo = respaldo.guardar_archivo(directorio, respaldo.PREFIJO_PREVIO, respaldo.exportar(s))
        respaldo.rotar(directorio, respaldo.PREFIJO_PREVIO, programador.CONSERVAR_PREVIOS)
        resultado = respaldo.restaurar(s, datos, incluir_usuarios=usuarios)
    except respaldo.RespaldoInvalido as e:
        s.rollback()
        raise HTTPException(400, str(e)) from None
    resultado["respaldo_previo"] = previo.name
    # si se restauraron los usuarios, el id de quien restaura puede ya no existir
    autor = None if resultado["usuarios_restaurados"] else u
    auditoria.registrar(s, autor, "datos", "restaurar", auditoria.CREAR, despues=resultado | {"por": u.usuario})
    s.commit()
    return resultado


@r.get("")
def exportar(s: Session = Depends(get_db), _=Depends(requiere("respaldo.exportar"))):
    return _descarga(respaldo.exportar(s), f"respaldo_control_procesos_{datetime.now():%Y-%m-%d}.json")


@r.post("/restaurar")
def restaurar(
    request: Request,
    datos: Annotated[dict, Body()],
    usuarios: bool = False,
    s: Session = Depends(get_db),
    u: Usuario = Depends(requiere("respaldo.restaurar")),
):
    """Reemplaza procesos, actuaciones y configuración. Antes guarda un respaldo del estado actual."""
    return _restaurar(s, u, _dir(request), datos, usuarios)


@r.get("/programacion")
def ver_programacion(s: Session = Depends(get_db), _=Depends(requiere("respaldo.exportar"))):
    return programador.leer_programacion(s)


@r.put("/programacion")
def editar_programacion(datos: Programacion, s: Session = Depends(get_db), u=Depends(requiere("respaldo.restaurar"))):
    antes = programador.leer_programacion(s)
    programador.guardar_programacion(s, datos.activo, datos.hora, datos.conservar)
    auditoria.registrar(s, u, "respaldo", "programacion", auditoria.EDITAR, antes=antes, despues=datos.model_dump())
    s.commit()
    return programador.leer_programacion(s)


@r.get("/archivos")
def archivos(request: Request, _=Depends(requiere("respaldo.exportar"))):
    return [
        {
            "nombre": p.name,
            "bytes": p.stat().st_size,
            "fecha": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            "automatico": p.name.startswith(respaldo.PREFIJO_AUTO),
        }
        for p in respaldo.listar_archivos(_dir(request))
    ]


@r.post("/archivos", status_code=201)
def crear_archivo(request: Request, s: Session = Depends(get_db), _=Depends(requiere("respaldo.exportar"))):
    return {"nombre": programador.respaldar_ahora(s, _dir(request)).name}


@r.get("/archivos/{nombre}")
def descargar_archivo(nombre: str, request: Request, _=Depends(requiere("respaldo.exportar"))):
    ruta = _archivo(request, nombre)
    return Response(
        ruta.read_bytes(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{ruta.name}"'},
    )


@r.post("/archivos/{nombre}/restaurar")
def restaurar_archivo(
    nombre: str,
    request: Request,
    usuarios: bool = False,
    s: Session = Depends(get_db),
    u: Usuario = Depends(requiere("respaldo.restaurar")),
):
    datos = json.loads(_archivo(request, nombre).read_text(encoding="utf-8"))
    return _restaurar(s, u, _dir(request), datos, usuarios)
