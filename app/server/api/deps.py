from collections.abc import Iterator
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.server.core.permisos import PERMISOS
from app.server.core.seguridad import hash_token
from app.server.db.models import Sesion, Usuario, ahora

COOKIE = "cp_sesion"
DURACION = timedelta(hours=12)


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.sesiones() as s:
        yield s


def permisos_de(u: Usuario) -> set[str]:
    if u.rol.es_sistema:
        return set(PERMISOS)
    return {p.permiso for p in u.rol.permisos} & PERMISOS.keys()


def usuario_actual(request: Request, s: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get(COOKIE)
    sesion = s.get(Sesion, hash_token(token)) if token else None
    momento = ahora()
    if not sesion or sesion.expira_en <= momento or not sesion.usuario.activo:
        raise HTTPException(401, "Sesión no válida o vencida")
    # sesión deslizante: se renueva con el uso, sin escribir en cada petición
    if sesion.expira_en - momento < DURACION / 2:
        sesion.expira_en = momento + DURACION
        s.commit()
    return sesion.usuario


def requiere(permiso: str):
    assert permiso in PERMISOS, permiso

    def dependencia(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if permiso not in permisos_de(u):
            raise HTTPException(403, f"No tiene permiso: {PERMISOS[permiso]}")
        return u

    return dependencia


def obtener(s: Session, modelo, clave, nombre: str = "Registro"):
    obj = s.get(modelo, clave)
    if obj is None:
        raise HTTPException(404, f"{nombre} no encontrado")
    return obj


def verificar_version(obj, version: int) -> None:
    if version != obj.version:
        raise HTTPException(409, "Otro usuario modificó este registro. Recargue e intente de nuevo.")
    obj.version += 1
