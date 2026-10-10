"""Automatismos de secretaría al registrar una actuación (v2 del HTML): fechas de gestión y ejecutoria."""

from dataclasses import dataclass
from datetime import date, timedelta

from app.server.domain.calendario import Calendario, calc_venc, es_habil
from app.server.domain.estados import ORIGEN_VENCIMIENTO, PASA_SI

EJEC_DIAS = 3
MAX_CORRIMIENTO = 20

CIERRE_PROVIDENCIA = "Providencia"
CIERRE_EJECUTORIA = "Ejecutoria"
CIERRE_CUMPLIMIENTO = "Cumplimiento"
CIERRE_AUDIENCIA_CANCELADA = "Audiencia cancelada"
MODOS_CIERRE = ("", CIERRE_PROVIDENCIA, CIERRE_EJECUTORIA, CIERRE_CUMPLIMIENTO)

SIN_NOTIFICACION = "sin_notificacion"
CORRE = "corre"
SUSPENDIDA = "suspendida"
EN_FIRME = "en_firme"

# catálogos del formulario de actuación (los de la v2, tal cual)
TIPOS_PROVIDENCIA = ("", "Auto interlocutorio", "Sentencia", "Medida cautelar")
RECURSOS = ("", "Reposición", "Apelación", "Queja", "Súplica", "Casación", "Impugnación", "Consulta")
OBJETOS_RECURSO = ("Auto", "Sentencia")
RESULTADOS_SUPERIOR = (
    "",
    "Confirman totalmente la decisión",
    "Modifican la decisión",
    "Revocan la decisión",
    "Decretan nulidad",
    "Inadmitidos",
    "Desiertos",
    "Desistidos",
)
NOTIF_FORMAS = ("", "Por estado", "Personal / electrónica", "Por edicto", "En estrados")
TRAMITES_POSTERIORES = (
    "",
    "Avalúos",
    "Liquidación de costas y créditos",
    "Remates",
    "Incidentes",
    "Solicitudes sobre medidas cautelares",
    "Entrega de inmuebles",
    "Otros",
)
SI_NO = ("", "Sí")


def fecha_gestion_secretaria(d: date | None, cal: Calendario) -> date | None:
    """La secretaría gestiona el mismo día si es hábil; si no, el siguiente hábil."""
    if not d:
        return None
    for _ in range(MAX_CORRIMIENTO):
        if es_habil(d, cal):
            break
        d += timedelta(days=1)
    return d


@dataclass(frozen=True)
class Ejecutoria:
    estado: str
    fecha: date | None = None
    # con recurso sin resolver: "superior" o "impugnacion"
    pendiente: str = ""


def ejecutoria(a, cal: Calendario) -> Ejecutoria:
    """Cuándo queda en firme la providencia: días hábiles tras la notificación, salvo recurso."""
    if not a.notif_fecha:
        return Ejecutoria(SIN_NOTIFICACION)
    if not a.recurso_tipo:
        return Ejecutoria(CORRE, calc_venc(a.notif_fecha, a.ejec_dias or EJEC_DIAS, True, cal))
    impugnada = a.rec_impug == PASA_SI
    if not a.superior_resultado:
        return Ejecutoria(SUSPENDIDA, pendiente="superior")
    if impugnada and not a.rec_impug_result:
        return Ejecutoria(SUSPENDIDA, pendiente="impugnacion")
    firme = (a.rec_impug_fecha or a.superior_fecha) if impugnada else a.superior_fecha
    return Ejecutoria(EN_FIRME, firme)


def autocompletar_actuacion(a, cal: Calendario) -> None:
    """Llena lo que la v2 llenaba sola al guardar; nunca pisa una fecha ya escrita."""
    if a.fecha_memorial and a.origen != ORIGEN_VENCIMIENTO:
        fg = fecha_gestion_secretaria(a.fecha_memorial, cal)
        if not a.constancia:
            a.constancia = fg
        if a.pasa == PASA_SI and not a.pase:
            a.pase = fg
    ej = ejecutoria(a, cal)
    if not a.ejecutoria and ej.fecha:
        a.ejecutoria = ej.fecha
    if a.modo_cierre == CIERRE_PROVIDENCIA and a.providencia:
        a.cumplida = a.providencia
    elif a.modo_cierre == CIERRE_EJECUTORIA and a.ejecutoria:
        a.cumplida = a.ejecutoria
