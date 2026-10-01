from datetime import date

from app.server.domain.estados import Contexto, fecha_activa, vencimiento
from app.server.domain.fechas_letras import fecha_larga, fecha_letras

TIPO_CONSTANCIA = "Constancia"
TIPO_PASE = "Pase al despacho"
CIUDAD_DEFECTO = "Chinácota"


def radicado_completo(prefijo: str | None, radicado: str | None) -> str:
    return f"{prefijo or ''}{radicado or ''}-00"


def ciudad_corta(ciudad: str | None) -> str:
    return (ciudad or CIUDAD_DEFECTO).split(" ")[0]


def fecha_doc(a, tipo: str, ctx: Contexto) -> date:
    """Fecha que sale impresa: la registrada para la constancia o el pase, no la del día."""
    activa = fecha_activa(a, ctx)
    if tipo == TIPO_PASE:
        candidatas = (a.pase, a.constancia, activa, a.fecha_memorial)
    else:
        candidatas = (a.constancia, activa, a.fecha_memorial, a.pase)
    return next((f for f in candidatas if f), ctx.hoy)


def fill_tpl(
    cuerpo: str, a, p, ctx: Contexto, *, prefijo: str = "", ciudad: str = "", motivo: str = "", fecha: date | None = None
) -> str:
    f = fecha or ctx.hoy
    venc = vencimiento(a, ctx) if a else None
    campos = {
        "{{radicado}}": p.radicado or "",
        "{{radicado_full}}": radicado_completo(prefijo, p.radicado),
        "{{proceso}}": p.clase or "",
        "{{demandante}}": p.demandante or "",
        "{{demandado}}": p.demandado or "",
        "{{cuaderno}}": (a.cuaderno or "") if a else "",
        "{{descripcion}}": (a.descripcion or "") if a else "",
        "{{materia}}": (a.materia or "") if a else "",
        "{{termino}}": (a.termino or "") if a else "",
        "{{fecha_inicio}}": fecha_larga(a.fecha_inicio) if a and a.fecha_inicio else "",
        "{{vencimiento}}": fecha_larga(venc) if venc else "",
        "{{motivo_pase}}": motivo or "",
        "{{fecha}}": fecha_larga(f),
        "{{fecha_letras}}": fecha_letras(f),
        "{{ciudad}}": ciudad_corta(ciudad),
    }
    for clave, valor in campos.items():
        cuerpo = cuerpo.replace(clave, valor)
    return cuerpo
