from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.server.api.config import CLAVES_JUZGADO, MEMBRETE
from app.server.api.deps import get_db, obtener, requiere
from app.server.api.esquemas import DocHtmlIn, DocTextoIn
from app.server.db.models import Actuacion, Config, Firmante, Plantilla
from app.server.domain.plantillas import fecha_doc, fill_tpl
from app.server.services.contexto import construir_contexto
from app.server.services.documentos import data_uri, html_documento

r = APIRouter(prefix="/api/actuaciones/{aid}/documento", tags=["documentos"])


def _juzgado(s: Session) -> dict:
    cfg = {c.clave: c.valor for c in s.scalars(select(Config).where(Config.clave.in_(CLAVES_JUZGADO)))}
    return {k: cfg.get(k, "") for k in CLAVES_JUZGADO}


@r.post("/texto")
def texto(aid: str, datos: DocTextoIn, s: Session = Depends(get_db), _=Depends(requiere("documentos.generar"))):
    """Texto de la plantilla ya diligenciado, para que el usuario lo ajuste antes de imprimir."""
    a = obtener(s, Actuacion, aid, "Actuación")
    plantilla = obtener(s, Plantilla, datos.plantilla_id, "Plantilla")
    ctx = construir_contexto(s)
    fecha = datos.fecha or fecha_doc(a, plantilla.tipo, ctx)
    jz = _juzgado(s)
    cuerpo = fill_tpl(
        plantilla.cuerpo, a, a.proceso, ctx, prefijo=jz["prefijo"], ciudad=jz["ciudad"], motivo=datos.motivo, fecha=fecha
    )
    return {"fecha": fecha.isoformat(), "cuerpo": cuerpo}


@r.post("/html", response_class=HTMLResponse)
def html(aid: str, datos: DocHtmlIn, s: Session = Depends(get_db), _=Depends(requiere("documentos.generar"))):
    a = obtener(s, Actuacion, aid, "Actuación")
    ctx = construir_contexto(s)
    firmante = s.get(Firmante, datos.firmante_id) if datos.firmante_id else None
    firmante = firmante or s.scalars(select(Firmante).order_by(Firmante.orden)).first()
    membrete = s.get(Config, MEMBRETE)
    return html_documento(
        proceso=a.proceso,
        cuerpo=datos.cuerpo,
        fecha=datos.fecha or ctx.hoy,
        membrete=data_uri(membrete.binario, membrete.valor) if membrete and membrete.binario else None,
        firmante=firmante,
        **_juzgado(s),
    )
