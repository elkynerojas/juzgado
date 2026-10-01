from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.server.api.deps import get_db, obtener, permisos_de, requiere, usuario_actual
from app.server.api.esquemas import RolIn, UsuarioEdicion, UsuarioNuevo
from app.server.core.permisos import PERMISOS
from app.server.core.seguridad import hash_password
from app.server.db.models import Rol, RolPermiso, Sesion, Usuario
from app.server.services import auditoria

r = APIRouter(prefix="/api", tags=["usuarios y roles"])


def usuario_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "usuario": u.usuario,
        "nombre": u.nombre,
        "rol_id": u.rol_id,
        "rol": u.rol.nombre,
        "activo": u.activo,
        "ultimo_acceso": u.ultimo_acceso.isoformat() if u.ultimo_acceso else None,
    }


def rol_dict(rol: Rol, usuarios: int = 0) -> dict:
    permisos = sorted(PERMISOS) if rol.es_sistema else sorted(p.permiso for p in rol.permisos)
    return {
        "id": rol.id,
        "nombre": rol.nombre,
        "descripcion": rol.descripcion,
        "es_sistema": rol.es_sistema,
        "permisos": permisos,
        "usuarios": usuarios,
    }


def _admins_activos(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(Usuario).join(Rol).where(Rol.es_sistema, Usuario.activo))


@r.get("/usuarios")
def listar_usuarios(s: Session = Depends(get_db), _=Depends(requiere("usuarios.gestionar"))):
    return [usuario_dict(u) for u in s.scalars(select(Usuario).order_by(Usuario.usuario))]


@r.post("/usuarios", status_code=201)
def crear_usuario(datos: UsuarioNuevo, s: Session = Depends(get_db), yo=Depends(requiere("usuarios.gestionar"))):
    if s.scalar(select(Usuario.id).where(func.lower(Usuario.usuario) == datos.usuario.lower())):
        raise HTTPException(409, "Ya existe un usuario con ese nombre")
    rol = obtener(s, Rol, datos.rol_id, "Rol")
    u = Usuario(usuario=datos.usuario, nombre=datos.nombre, password_hash=hash_password(datos.password), rol=rol)
    s.add(u)
    s.flush()
    auditoria.registrar(s, yo, "usuario", u.id, auditoria.CREAR, despues=usuario_dict(u))
    s.commit()
    return usuario_dict(u)


@r.put("/usuarios/{uid}")
def editar_usuario(
    uid: int, datos: UsuarioEdicion, s: Session = Depends(get_db), yo=Depends(requiere("usuarios.gestionar"))
):
    u = obtener(s, Usuario, uid, "Usuario")
    rol = obtener(s, Rol, datos.rol_id, "Rol")
    antes = usuario_dict(u)
    deja_de_ser_admin = u.rol.es_sistema and u.activo and not (rol.es_sistema and datos.activo)
    if deja_de_ser_admin and _admins_activos(s) <= 1:
        raise HTTPException(409, "Debe quedar al menos un administrador activo")
    u.nombre, u.rol, u.activo = datos.nombre, rol, datos.activo
    if datos.password:
        u.password_hash = hash_password(datos.password)
    if datos.password or not datos.activo:
        s.execute(delete(Sesion).where(Sesion.usuario_id == u.id))
    despues = usuario_dict(u) | ({"password": "cambiada"} if datos.password else {})
    auditoria.registrar(s, yo, "usuario", u.id, auditoria.EDITAR, antes=antes, despues=despues)
    s.commit()
    return usuario_dict(u)


@r.get("/permisos")
def catalogo_permisos(_=Depends(usuario_actual)):
    return [{"clave": k, "descripcion": v, "modulo": k.split(".")[0]} for k, v in PERMISOS.items()]


@r.get("/roles")
def listar_roles(s: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    if not permisos_de(u) & {"usuarios.gestionar", "roles.gestionar"}:
        raise HTTPException(403, "No tiene permiso para ver los roles")
    conteo = dict(s.execute(select(Usuario.rol_id, func.count()).group_by(Usuario.rol_id)).all())
    return [rol_dict(rol, conteo.get(rol.id, 0)) for rol in s.scalars(select(Rol).order_by(Rol.id))]


def _validar_rol(s: Session, datos: RolIn, rol_id: int | None) -> None:
    desconocidos = set(datos.permisos) - PERMISOS.keys()
    if desconocidos:
        raise HTTPException(422, f"Permisos desconocidos: {', '.join(sorted(desconocidos))}")
    repetido = s.scalar(select(Rol.id).where(func.lower(Rol.nombre) == datos.nombre.lower(), Rol.id != (rol_id or 0)))
    if repetido:
        raise HTTPException(409, "Ya existe un rol con ese nombre")


@r.post("/roles", status_code=201)
def crear_rol(datos: RolIn, s: Session = Depends(get_db), yo=Depends(requiere("roles.gestionar"))):
    _validar_rol(s, datos, None)
    rol = Rol(nombre=datos.nombre, descripcion=datos.descripcion)
    rol.permisos = [RolPermiso(permiso=p) for p in sorted(set(datos.permisos))]
    s.add(rol)
    s.flush()
    auditoria.registrar(s, yo, "rol", rol.id, auditoria.CREAR, despues=rol_dict(rol))
    s.commit()
    return rol_dict(rol)


@r.put("/roles/{rid}")
def editar_rol(rid: int, datos: RolIn, s: Session = Depends(get_db), yo=Depends(requiere("roles.gestionar"))):
    rol = obtener(s, Rol, rid, "Rol")
    if rol.es_sistema:
        raise HTTPException(400, "El rol Administrador no se puede modificar")
    _validar_rol(s, datos, rid)
    antes = rol_dict(rol)
    rol.nombre, rol.descripcion = datos.nombre, datos.descripcion
    actuales = {p.permiso: p for p in rol.permisos}
    rol.permisos = [actuales.get(p) or RolPermiso(permiso=p) for p in sorted(set(datos.permisos))]
    s.flush()
    auditoria.registrar(s, yo, "rol", rol.id, auditoria.EDITAR, antes=antes, despues=rol_dict(rol))
    s.commit()
    return rol_dict(rol)


@r.delete("/roles/{rid}", status_code=204)
def eliminar_rol(rid: int, s: Session = Depends(get_db), yo=Depends(requiere("roles.gestionar"))):
    rol = obtener(s, Rol, rid, "Rol")
    if rol.es_sistema:
        raise HTTPException(400, "El rol Administrador no se puede eliminar")
    if s.scalar(select(func.count()).select_from(Usuario).where(Usuario.rol_id == rid)):
        raise HTTPException(409, "Hay usuarios con este rol; cámbieles el rol primero")
    auditoria.registrar(s, yo, "rol", rol.id, auditoria.ELIMINAR, antes=rol_dict(rol))
    s.delete(rol)
    s.commit()
