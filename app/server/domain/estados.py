"""Situación de actuaciones y procesos. Nada de esto se guarda: se deriva de las fechas."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from app.server.domain.calendario import Calendario, calc_venc

PERSONALIZADO = "(personalizado)"
ORIGEN_VENCIMIENTO = "Vencimiento de término"
PASA_SI = "Sí"

SIT = (
    "Cumplida / cerrada",
    "Esperando término / evento",
    "Falta fecha que activa",
    "Secretaría: sin constancia",
    "Secretaría: falta pasar al despacho",
    "Al despacho: pendiente proveer",
    "Proveído: corre ejecutoria / notificación",
    "Ejecutoriado: pendiente cumplir",
    "Secretaría: trámite (no requiere juez)",
    "En trámite",
)
SIT_BADGE = ("b-gray", "b-blue", "b-amber", "b-red", "b-red", "b-red", "b-teal", "b-teal", "b-slate", "b-slate")


@dataclass(frozen=True)
class TerminoInfo:
    dias: int | None
    habil: bool


@dataclass(frozen=True)
class Contexto:
    hoy: date
    calendario: Calendario
    terminos: Mapping[str, TerminoInfo]


@dataclass(frozen=True)
class ActDeriv:
    act: object
    codigo: int
    ubicacion: str
    dias: int


@dataclass(frozen=True)
class ProcDeriv:
    acts: tuple[ActDeriv, ...]
    vivas: int
    rep_despacho: int
    rep_secretaria: int
    en_secretaria: bool
    en_despacho: bool
    inactividad: str
    proximo: date | None
    dias_sin_mov: int


def term_info(a, ctx: Contexto) -> TerminoInfo | None:
    if not a.termino:
        return None
    if a.termino == PERSONALIZADO:
        return TerminoInfo(a.termino_dias, a.termino_habil is not False)
    return ctx.terminos.get(a.termino)


def vencimiento(a, ctx: Contexto) -> date | None:
    ti = term_info(a, ctx)
    if not ti or not a.fecha_inicio:
        return None
    return calc_venc(a.fecha_inicio, ti.dias, ti.habil, ctx.calendario)


def fecha_activa(a, ctx: Contexto) -> date | None:
    if a.origen == ORIGEN_VENCIMIENTO:
        return vencimiento(a, ctx)
    return a.fecha_memorial or None


def codigo(a, ctx: Contexto) -> int:
    f = fecha_activa(a, ctx)
    if a.cumplida:
        return 0
    if not f:
        return 2
    if f > ctx.hoy:
        return 1
    if not a.constancia:
        return 3
    if a.pasa == PASA_SI and not a.pase:
        return 4
    if a.pase and not a.providencia:
        return 5
    if a.providencia and not a.ejecutoria:
        return 6
    if a.ejecutoria:
        return 7
    if (a.pasa or "").startswith("No"):
        return 8
    return 9


def ubicacion(c: int) -> str:
    if c == 5:
        return "Despacho"
    if c in (0, 2):
        return ""
    return "Secretaría"


def viva(c: int) -> bool:
    return c != 0


def dias_estado(a, c: int, ctx: Contexto) -> int:
    desde = None
    if c == 3:
        desde = fecha_activa(a, ctx)
    elif c in (4, 8):
        desde = a.constancia
    elif c == 5:
        desde = a.pase
    elif c == 6:
        desde = a.providencia
    elif c == 7:
        desde = a.ejecutoria
    return (ctx.hoy - desde).days if desde else 0


def est_termino(a, ctx: Contexto) -> str:
    if not term_info(a, ctx):
        return ""
    if a.suspende:
        return "Suspendido"
    if not a.fecha_inicio:
        return "Latente"
    v = vencimiento(a, ctx)
    if not v:
        return ""
    faltan = (v - ctx.hoy).days
    if faltan < 0:
        return "Vencido"
    if faltan <= 3:
        return "Próximo a vencer"
    return "En término"


def resultado(a, c: int, ctx: Contexto) -> tuple[str, str]:
    if c == 0:
        return ("Atendido / cerrado", "b-green")
    if 4 <= c <= 7:
        return ("Atendido — en decisión/cierre", "b-teal")
    if c == 3 and est_termino(a, ctx) == "Vencido":
        return ("Venció sin respuesta", "b-red")
    if c == 1:
        return ("En plazo", "b-blue")
    if c == 3:
        return ("Recibido — falta constancia", "b-amber")
    return ("", "")


def derivar(a, ctx: Contexto) -> ActDeriv:
    c = codigo(a, ctx)
    return ActDeriv(a, c, ubicacion(c), dias_estado(a, c, ctx))


def proc_deriv(situacion: str, acts: Iterable, ctx: Contexto) -> ProcDeriv:
    ds = tuple(derivar(a, ctx) for a in acts)
    vivas = [x for x in ds if viva(x.codigo)]
    cods = {x.codigo for x in vivas}
    rep_d = sum(1 for x in vivas if x.codigo == 5)
    rep_s = sum(1 for x in vivas if x.codigo in (3, 4))
    if situacion == "Suspendido":
        inact = "— (suspendido)"
    elif situacion == "Apelado":
        inact = "En el superior"
    elif rep_d:
        inact = "Juzgado (despacho)"
    elif rep_s or cods & {6, 7, 8}:
        inact = "Juzgado (secretaría)"
    elif 1 in cods:
        inact = "Parte (corre término)"
    elif not vivas:
        inact = "Sin actuaciones vivas"
    else:
        inact = "Sin carga"
    futuras = [f for x in vivas if x.codigo == 1 and (f := fecha_activa(x.act, ctx))]
    return ProcDeriv(
        acts=ds,
        vivas=len(vivas),
        rep_despacho=rep_d,
        rep_secretaria=rep_s,
        en_secretaria=any(x.ubicacion == "Secretaría" for x in vivas),
        en_despacho=any(x.ubicacion == "Despacho" for x in vivas),
        inactividad=inact,
        proximo=min(futuras, default=None),
        dias_sin_mov=max([0, *(x.dias for x in vivas)]),
    )


def global_stats(acts: Iterable, ctx: Contexto) -> dict:
    por_situacion = [0] * len(SIT)
    en_despacho = en_secretaria = 0
    proximos = []
    for a in acts:
        c = codigo(a, ctx)
        por_situacion[c] += 1
        u = ubicacion(c)
        if viva(c) and u == "Despacho":
            en_despacho += 1
        if viva(c) and u == "Secretaría":
            en_secretaria += 1
        if c == 1 and (f := fecha_activa(a, ctx)):
            proximos.append((f, a, a.descripcion))
        # v2: también avisa cuándo queda en firme una providencia notificada sin recurso
        if a.notif_fecha and not a.recurso_tipo:
            ev = calc_venc(a.notif_fecha, a.ejec_dias or 3, True, ctx.calendario)
            if ev and ev >= ctx.hoy:
                proximos.append((ev, a, f"Ejecutoria/recursos — {a.descripcion or ''}"))
    proximos.sort(key=lambda x: x[0])
    return {
        "sin_constancia": por_situacion[3],
        "falta_pasar": por_situacion[4],
        "al_despacho": por_situacion[5],
        "por_situacion": por_situacion,
        "en_despacho": en_despacho,
        "en_secretaria": en_secretaria,
        "proximos": proximos,
    }
