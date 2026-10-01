from sqlalchemy.orm import Session

from app.server.db.models import Auditoria, Usuario

CREAR, EDITAR, ELIMINAR = "crear", "editar", "eliminar"


def registrar(
    s: Session, usuario: Usuario | None, entidad: str, entidad_id, accion: str, antes=None, despues=None
) -> None:
    s.add(
        Auditoria(
            usuario_id=usuario.id if usuario else None,
            usuario_nombre=usuario.usuario if usuario else "",
            entidad=entidad,
            entidad_id=str(entidad_id),
            accion=accion,
            antes=antes,
            despues=despues,
        )
    )
