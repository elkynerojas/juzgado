"""Actuaciones que se crean solas al guardar un proceso (v2 del HTML).

Las funciones no tocan la base: reciben el proceso y sus actuaciones, modifican las existentes en sitio
y devuelven las nuevas para que quien llama las agregue a la sesión.
"""

import re
from collections.abc import Collection, Iterable
from datetime import date, datetime, time

from app.server.db.models import Actuacion, nuevo_id
from app.server.domain import naturaleza as N
from app.server.domain.calendario import Calendario
from app.server.domain.estados import PASA_SI, PERSONALIZADO
from app.server.domain.secretaria import CIERRE_AUDIENCIA_CANCELADA, fecha_gestion_secretaria

RUTA_GARANTIAS = "r_garantias"
TIPO_GESTION_GARANTIAS = "Solicitudes de control de garantías"
TIPO_CANCELACION = "Cancelación de audiencia de control de garantías"
MATERIA_AUDIENCIA = "Audiencia / diligencia"
MATERIA_ADMISION = "Admisión / subsanación"
TERMINO_ADMISION = "Estudio de admisibilidad"
PASA_NO = "No – trámite secretaría"
AUD_PROGRAMADA = "Programada"
AUD_CANCELADA = "Cancelada / no realizada"

# detalle de la salida no efectiva de una solicitud de garantías
DETALLE_RETIRO_FISCALIA = "Retiro de la solicitud por la Fiscalía"
DETALLE_RETIRO_PARTES = "Retiro de la solicitud por las demás partes"
DETALLES_SALIDA_NO_EFECTIVA = (
    DETALLE_RETIRO_FISCALIA,
    DETALLE_RETIRO_PARTES,
    "Muerte del indiciado",
    "Otra circunstancia sin decisión de fondo",
)
# causas de cancelación: son las llaves de la columna SIERJU (la v2 usaba otros textos y no se contaban)
CAUSA_RETIRO_FISCAL = "Retiro de la solicitud por el fiscal"
CAUSA_RETIRO_PARTES = "Retiro de la solicitud de las demás partes"
CAUSA_OTRAS = "Otras causas"

_FIN_DEL_DIA = time(23, 59)


def _nueva(p, **campos) -> Actuacion:
    base = dict(
        id=nuevo_id(),
        proceso_id=p.id,
        cuaderno=p.cuaderno_inicial or "Principal",
        tipo_solicitud="",
        origen="Memorial",
        descripcion="",
        constancia=None,
        pasa="",
        pase=None,
        providencia=None,
        ejecutoria=None,
        cumplida=None,
        termino="",
        termino_dias=None,
        termino_habil=True,
        fecha_inicio=None,
        suspende=False,
        obs="",
        ruta_id="",
        paso_idx=None,
        tipo_providencia="",
        modo_cierre="",
        salida_stat="",
        entrada_stat="",
        es_audiencia=False,
        aud_fecha=None,
        aud_hora="",
        aud_estado="",
        aud_tipo="",
        aud_causa="",
        aud_inmediata=False,
        cancelacion_de="",
    )
    return Actuacion(**(base | campos))


def _de(p, acts: Iterable) -> list:
    return [a for a in acts if a.proceso_id == p.id]


CUADERNO_MEDIDAS = "Medidas cautelares"
SITUACION_TERMINADO = "Terminado"
SITUACION_ARCHIVADO = "Archivado"


def normalizar_proceso(p, hoy: date, crear_medidas: bool = False) -> None:
    """Lo que la v2 completaba sola en saveProc antes de guardar. Modifica el proceso en sitio."""
    if p.situacion == SITUACION_TERMINADO and not p.fecha_terminacion:
        p.fecha_terminacion = hoy
    if p.situacion == SITUACION_ARCHIVADO and not p.fecha_archivo:
        p.fecha_archivo = hoy

    p.fecha_tramite_posterior = (p.fecha_tramite_posterior or p.fecha_terminacion or hoy) if p.tramite_posterior else None

    p.cuaderno_inicial = p.cuaderno_inicial or "Principal"
    cuadernos = list(p.cuadernos or [])
    for c in (p.cuaderno_inicial, CUADERNO_MEDIDAS if crear_medidas else None):
        if c and c not in cuadernos:
            cuadernos.append(c)
    p.cuadernos = cuadernos

    if N.es_penal(p.naturaleza):
        # en penal la clase del proceso es el delito, que es también el tipo SIERJU
        p.clase = p.tipo_sierju
        p.delitos_adicionales = [d for d in (p.delitos_adicionales or []) if d]
    else:
        p.delitos_adicionales = []

    if N.es_garantias(p.naturaleza):
        # la salida se lleva por solicitud, no por proceso (en la v2 el campo quedaba oculto y se guardaba igual)
        p.forma_salida = ""
        for s in p.solicitudes_penales:
            if not s.fecha:
                s.fecha = p.fecha_rad
        primera = p.solicitudes_penales[0] if p.solicitudes_penales else None
        p.solicitud_penal = primera.tipo if primera else ""
    else:
        p.solicitudes_penales = []


def gestion_garantias(p, acts: Iterable, cal: Calendario) -> tuple[Actuacion, bool]:
    """Una sola actuación de radicación para todas las solicitudes de garantías. Devuelve (actuación, es_nueva)."""
    sols = list(p.solicitudes_penales)
    tipos = [s.tipo for s in sols if s.tipo]
    f = (sols[0].fecha if sols else None) or p.fecha_rad
    fg = fecha_gestion_secretaria(f, cal)
    desc = "Se radican " + (f"{len(tipos)} solicitudes de control de garantías" if len(tipos) > 1 else "solicitud de control de garantías")
    if tipos:
        desc += ": " + " · ".join(tipos)
    existente = next((a for a in _de(p, acts) if a.ruta_id == RUTA_GARANTIAS and a.paso_idx == 0), None)
    if existente:
        existente.descripcion = desc
        existente.fecha_memorial = f
        existente.constancia = existente.constancia or fg
        existente.pasa = existente.pasa or PASA_SI
        existente.pase = existente.pase or fg
        return existente, False
    nueva = _nueva(
        p,
        materia=MATERIA_AUDIENCIA,
        tipo_solicitud=TIPO_GESTION_GARANTIAS,
        descripcion=desc,
        fecha_memorial=f,
        constancia=fg,
        pasa=PASA_SI,
        pase=fg,
        obs="Radicación conjunta; las solicitudes se contabilizan individualmente en SIERJU",
        ruta_id=RUTA_GARANTIAS,
        paso_idx=0,
    )
    return nueva, True


def causa_cancelacion(sols: Iterable) -> str:
    detalles = {s.detalle_salida for s in sols}
    if DETALLE_RETIRO_FISCALIA in detalles:
        return CAUSA_RETIRO_FISCAL
    if DETALLE_RETIRO_PARTES in detalles:
        return CAUSA_RETIRO_PARTES
    return CAUSA_OTRAS


def _hora(texto: str | None) -> time:
    m = re.match(r"^(\d{1,2}):(\d{2})", texto or "")
    if not m:
        return _FIN_DEL_DIA
    return time(min(int(m[1]), 23), min(int(m[2]), 59))


def _momento(d: date, hora: str | None) -> datetime:
    return datetime.combine(d, _hora(hora))


def sync_audiencia_cancelada(p, acts: Iterable) -> list[Actuacion]:
    """Si todas las solicitudes salieron antes de la audiencia fijada, la registra como cancelada (sin borrar nada)."""
    if not N.es_garantias(p.naturaleza):
        return []
    sols = list(p.solicitudes_penales)
    if not sols or any(not s.salida or not s.fecha_salida for s in sols):
        return []
    propias = _de(p, acts)
    ultima = max(s.fecha_salida for s in sols)
    causa = causa_cancelacion(sols)
    nuevas = []
    for a in propias:
        if not (a.ruta_id == RUTA_GARANTIAS and a.paso_idx == 1 and a.es_audiencia and a.aud_fecha):
            continue
        aud = _momento(a.aud_fecha, a.aud_hora)
        if not all(_momento(s.fecha_salida, s.hora_salida) < aud for s in sols):
            continue
        desc = "Audiencia cancelada / no realizada por terminación previa de las solicitudes"
        ya = next((x for x in propias if x.cancelacion_de == a.id), None)
        if ya:
            ya.aud_fecha, ya.aud_hora, ya.aud_causa, ya.descripcion = a.aud_fecha, a.aud_hora or "", causa, desc
            continue
        nuevas.append(
            _nueva(
                p,
                cuaderno=a.cuaderno or p.cuaderno_inicial or "Principal",
                materia=MATERIA_AUDIENCIA,
                tipo_solicitud=TIPO_CANCELACION,
                origen="Oficiosa",
                descripcion=desc,
                fecha_memorial=ultima,
                pasa=PASA_NO,
                cumplida=ultima,
                obs="Generada automáticamente al verificarse que todas las solicitudes terminaron antes de la audiencia fijada.",
                es_audiencia=True,
                aud_fecha=a.aud_fecha,
                aud_hora=a.aud_hora or "",
                aud_estado=AUD_CANCELADA,
                aud_tipo=a.aud_tipo or "",
                aud_causa=causa,
                ruta_id=RUTA_GARANTIAS,
                paso_idx=2,
                modo_cierre=CIERRE_AUDIENCIA_CANCELADA,
                cancelacion_de=a.id,
            )
        )
    return nuevas


def crear_actuacion_inicial(p, acts: Iterable, cal: Calendario, terminos: Collection[str], crear: bool) -> list[Actuacion]:
    """La actuación con que arranca el proceso. En garantías siempre se crea la gestión de las solicitudes."""
    nat = p.naturaleza
    if N.es_garantias(nat):
        a, nueva = gestion_garantias(p, acts, cal)
        return [a] if nueva else []
    if not crear or not p.fecha_rad:
        return []
    if N.es_penal(nat):
        tipo = p.tipo_entrada or "Solicitud penal"
        desc = f"Se radica {tipo.lower()}"
    elif nat == N.TUTELA:
        tipo, desc = "Acción de tutela", "Se radica acción de tutela"
    elif nat == N.DESACATO:
        tipo, desc = "Solicitud de incidente de desacato", "Se registra actuación inicial"
    else:
        tipo = "Demanda"
        desc = "Se radica demanda" if nat in (N.CIVIL, N.FAMILIA) else "Se registra actuación inicial"
    termino, dias, inicio = "", None, None
    if nat in (N.TUTELA, N.DESACATO):
        termino, dias, inicio = PERSONALIZADO, 10, p.fecha_rad
        desc += " — término de 10 días hábiles para resolver"
    elif nat in (N.CIVIL, N.FAMILIA):
        termino = TERMINO_ADMISION if TERMINO_ADMISION in terminos else ""
        inicio = p.fecha_rad
    fg = fecha_gestion_secretaria(p.fecha_rad, cal)
    return [
        _nueva(
            p,
            materia=MATERIA_AUDIENCIA if N.es_penal(nat) else MATERIA_ADMISION,
            tipo_solicitud=tipo,
            descripcion=desc,
            fecha_memorial=p.fecha_rad,
            constancia=fg,
            pasa=PASA_SI,
            pase=fg,
            termino=termino,
            termino_dias=dias,
            fecha_inicio=inicio,
            obs="Creada automáticamente con el proceso",
            entrada_stat=p.tipo_entrada or tipo,
        )
    ]


def al_guardar_proceso(
    p, acts: Iterable, cal: Calendario, terminos: Collection[str], nuevo: bool, crear_inicial: bool = True
) -> list[Actuacion]:
    """Lo que hacía saveProc de la v2 después de guardar. Devuelve las actuaciones nuevas."""
    acts = list(acts)
    if nuevo:
        nuevas = crear_actuacion_inicial(p, acts, cal, terminos, crear_inicial)
    elif N.es_garantias(p.naturaleza):
        a, es_nueva = gestion_garantias(p, acts, cal)
        nuevas = [a] if es_nueva else []
    else:
        return []
    return nuevas + sync_audiencia_cancelada(p, acts + nuevas)


def siguiente_cuaderno_incidente(base: str, existentes: Iterable[str]) -> str:
    """"Incidente 3" si ya hay "Incidente 1" e "Incidente 2" (sin distinguir mayúsculas)."""
    rx = re.compile(rf"^{re.escape(base)}\s*(\d+)$", re.I)
    n = max((int(m[1]) for c in existentes if (m := rx.match(c or ""))), default=0)
    return f"{base} {n + 1}"
