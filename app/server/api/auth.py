from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.server.api.deps import COOKIE, DURACION, get_db, permisos_de, usuario_actual
from app.server.api.esquemas import CambioPassword, Instalacion, Login
from app.server.core.permisos import ROL_ADMIN
from app.server.core.seguridad import hash_password, hash_token, nuevo_token, verificar_password
from app.server.db.models import Rol, Sesion, Usuario, ahora
from app.server.services import auditoria

r = APIRouter(prefix="/api", tags=["autenticación"])

MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=5)


def _abrir_sesion(s: Session, u: Usuario, respuesta: Response) -> None:
    token = nuevo_token()
    momento = ahora()
    s.execute(delete(Sesion).where(Sesion.expira_en <= momento))
    s.add(Sesion(token_hash=hash_token(token), usuario_id=u.id, expira_en=momento + DURACION))
    u.ultimo_acceso = momento
    respuesta.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=int(DURACION.total_seconds()))


def yo_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "usuario": u.usuario,
        "nombre": u.nombre,
        "rol": u.rol.nombre,
        "permisos": sorted(permisos_de(u)),
        "preferencias": u.preferencias or {},
    }


@r.get("/estado")
def estado(s: Session = Depends(get_db)):
    return {"inicializado": bool(s.scalar(select(func.count()).select_from(Usuario)))}


@r.post("/instalacion", status_code=201)
def instalacion(datos: Instalacion, respuesta: Response, s: Session = Depends(get_db)):
    """Primer arranque: crea el administrador. Solo funciona mientras no exista ningún usuario."""
    if s.scalar(select(func.count()).select_from(Usuario)):
        raise HTTPException(409, "El sistema ya fue inicializado")
    rol = s.scalars(select(Rol).where(Rol.nombre == ROL_ADMIN)).one()
    u = Usuario(usuario=datos.usuario, nombre=datos.nombre, password_hash=hash_password(datos.password), rol=rol)
    s.add(u)
    s.flush()
    auditoria.registrar(s, u, "usuario", u.id, auditoria.CREAR, despues={"usuario": u.usuario, "rol": rol.nombre})
    _abrir_sesion(s, u, respuesta)
    s.commit()
    return yo_dict(u)


@r.post("/auth/login")
def login(datos: Login, request: Request, respuesta: Response, s: Session = Depends(get_db)):
    intentos: dict[str, tuple[int, datetime]] = request.app.state.intentos
    clave = datos.usuario.strip().lower()
    fallos, hasta = intentos.get(clave, (0, ahora()))
    if fallos >= MAX_INTENTOS and hasta > ahora():
        raise HTTPException(429, "Demasiados intentos fallidos. Espere unos minutos.")
    u = s.scalars(select(Usuario).where(func.lower(Usuario.usuario) == clave)).first()
    if not u or not u.activo or not verificar_password(u.password_hash, datos.password):
        intentos[clave] = (fallos % MAX_INTENTOS + 1, ahora() + BLOQUEO)
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    intentos.pop(clave, None)
    _abrir_sesion(s, u, respuesta)
    s.commit()
    return yo_dict(u)


@r.post("/auth/logout", status_code=204)
def logout(request: Request, respuesta: Response, s: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        s.execute(delete(Sesion).where(Sesion.token_hash == hash_token(token)))
        s.commit()
    respuesta.delete_cookie(COOKIE)


@r.get("/me")
def yo(u: Usuario = Depends(usuario_actual)):
    return yo_dict(u)


@r.put("/me/preferencias")
def preferencias(datos: dict, u: Usuario = Depends(usuario_actual), s: Session = Depends(get_db)):
    u.preferencias = {k: datos.get(k) or "" for k in ("color", "modo", "font")}
    s.commit()
    return u.preferencias


@r.put("/me/password", status_code=204)
def cambiar_password(
    datos: CambioPassword, request: Request, u: Usuario = Depends(usuario_actual), s: Session = Depends(get_db)
):
    if not verificar_password(u.password_hash, datos.actual):
        raise HTTPException(400, "La contraseña actual no coincide")
    u.password_hash = hash_password(datos.nueva)
    # cierra las demás sesiones del usuario
    actual = hash_token(request.cookies[COOKIE])
    s.execute(delete(Sesion).where(Sesion.usuario_id == u.id, Sesion.token_hash != actual))
    auditoria.registrar(s, u, "usuario", u.id, auditoria.EDITAR, despues={"password": "cambiada"})
    s.commit()
