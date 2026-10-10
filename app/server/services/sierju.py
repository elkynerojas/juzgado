from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.db.models import Proceso
from app.server.domain.naturaleza import sug_sierju


def completar_tipos_sierju(s: Session) -> int:
    """Sugiere el tipo SIERJU a los procesos que no lo tienen (los que vienen del HTML v1 o de respaldos viejos)."""
    n = 0
    for p in s.scalars(select(Proceso).where(Proceso.tipo_sierju == "")):
        if tipo := sug_sierju(p.clase, p.naturaleza):
            p.tipo_sierju = tipo
            n += 1
    s.flush()
    return n
