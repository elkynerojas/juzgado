"""Audiencias: estados, tipos y causas (v2 del HTML).

Las causas salen de las columnas SIERJU, no de la lista genérica de la v2: esa lista tenía etiquetas que no
coincidían con ninguna columna ("Causa demás partes" en vez de "Causa de las demás partes", entre otras), así
que la causa se guardaba pero nunca llegaba a la estadística.
"""

from collections.abc import Iterable
from datetime import date, timedelta

from app.server.db.models import Actuacion, nuevo_id
from app.server.db.seeds import cargar_sierju
from app.server.domain import naturaleza as N

PROGRAMADA = "Programada"
REALIZADA = "Realizada"
SUSPENDIDA = "Suspendida"
APLAZADA = "Aplazada"
CANCELADA = "Cancelada / no realizada"
ESTADOS = (PROGRAMADA, REALIZADA, SUSPENDIDA, APLAZADA, CANCELADA)

MATERIA = "Audiencia / diligencia"


def lleva_causa(estado: str | None) -> bool:
    """Solo aplazar y cancelar piden causa; el resto de estados la dejan vacía."""
    return bool(estado) and ("Aplaz" in estado or "Cancel" in estado)


def _clave_causa(nat: str | None, estado: str | None) -> str:
    rama = "penal" if N.es_penal(nat) else "civil"
    return f"{rama}_{'aplazada' if 'Aplaz' in (estado or '') else 'cancelada'}"


def causas(nat: str | None, estado: str | None) -> list[str]:
    if not lleva_causa(estado):
        return []
    return list(cargar_sierju()["audiencias"]["columnas_causa"][_clave_causa(nat, estado)])


# la clase de audiencia según la etapa, por naturaleza penal exacta; el resto usa la lista completa
_TIPOS_PENALES = {
    "Penal 906 - Garantías": ("Ley 906 Garantías", "Otras audiencias"),
    "Penal 906 - Conocimiento": (
        "Ley 906 Conocimiento - Formulación de acusación",
        "Ley 906 Conocimiento - Preparatoria",
        "Ley 906 Conocimiento - Juicio oral",
        "Ley 906 Conocimiento - Lectura de fallo",
        "Otras audiencias",
    ),
    "Penal 1826 - Garantías": ("Ley 1826 Garantías adultos", "Ley 1826 Audiencia concentrada", "Otras audiencias"),
    "Penal 1826 - Conocimiento": ("Ley 1826 Audiencia concentrada", "Ley 1826 Audiencia de juicio", "Otras audiencias"),
}


def tipos(nat: str | None) -> list[str]:
    a = cargar_sierju()["audiencias"]
    if not N.es_penal(nat):
        return list(a["tipos_civil_familia"])
    if nat in _TIPOS_PENALES:
        # se filtran contra la semilla para no duplicar las etiquetas en dos sitios
        propios = _TIPOS_PENALES[nat]
        return [t for t in a["tipos_penal"] if t in propios]
    return list(a["tipos_penal"])


def estado_de(a) -> str:
    return a.aud_estado or PROGRAMADA


def es_audiencia(a) -> bool:
    return bool(a.es_audiencia and a.aud_fecha)


def ordenar(acts: Iterable) -> list:
    """Por fecha y hora, como el localeCompare de la v2; sin hora van primero dentro del día."""
    return sorted(acts, key=lambda a: (a.aud_fecha, a.aud_hora or ""))


def pendientes(acts: Iterable, hoy: date) -> list:
    """Audiencias que siguen "Programada" cuando su fecha ya llegó: hay que confirmar qué pasó."""
    return ordenar(a for a in acts if es_audiencia(a) and estado_de(a) == PROGRAMADA and a.aud_fecha <= hoy)


def proximas(acts: Iterable, hoy: date, dias: int) -> list:
    limite = hoy + timedelta(days=dias)
    return ordenar(
        a for a in acts if es_audiencia(a) and estado_de(a) == PROGRAMADA and hoy < a.aud_fecha <= limite
    )


# ---------- fijar, resolver y reprogramar ----------

ORIGEN = "Providencia (auto/sentencia)"


def _nueva(p, *, cuaderno, fecha, hora, tipo, estado, causa, asignado_a, descripcion, obs) -> Actuacion:
    return Actuacion(
        id=nuevo_id(),
        proceso_id=p.id,
        cuaderno=cuaderno or p.cuaderno_inicial or "Principal",
        materia=MATERIA,
        tipo_solicitud="",
        origen=ORIGEN,
        descripcion=descripcion,
        fecha_memorial=fecha,
        termino_habil=True,
        obs=obs,
        es_audiencia=True,
        aud_fecha=fecha,
        aud_hora=hora or "",
        aud_estado=estado,
        aud_tipo=tipo or "",
        aud_causa=causa if lleva_causa(estado) else "",
        asignado_a=asignado_a or "",
    )


def fijar(p, *, cuaderno="", fecha, hora="", tipo="", estado=PROGRAMADA, causa="", asignado_a="") -> Actuacion:
    """La audiencia que se fija directamente desde el panel, sin pasar por una providencia."""
    return _nueva(
        p, cuaderno=cuaderno, fecha=fecha, hora=hora, tipo=tipo, estado=estado, causa=causa,
        asignado_a=asignado_a, descripcion=f"Audiencia: {tipo}".strip(": ").strip(), obs="",
    )  # fmt: skip


def resolver(a, estado: str, causa: str = "") -> None:
    """Registra qué pasó con la audiencia. La causa solo se guarda si el estado la pide."""
    a.aud_estado = estado
    a.aud_causa = causa if lleva_causa(estado) else ""


def reprogramar(p, origen, *, fecha, hora="", tipo="") -> Actuacion:
    """La audiencia que nace dentro de otra: reprogramada si se aplazó o suspendió, nueva en cualquier otro caso."""
    tipo = tipo or origen.aud_tipo or ""
    reprog = "Aplaz" in (origen.aud_estado or "") or origen.aud_estado == SUSPENDIDA
    prefijo = "Audiencia reprogramada: " if reprog else "Nueva audiencia fijada en diligencia: "
    return _nueva(
        p, cuaderno=origen.cuaderno, fecha=fecha, hora=hora, tipo=tipo, estado=PROGRAMADA, causa="",
        asignado_a=origen.asignado_a, descripcion=prefijo + tipo,
        obs=f"Fijada desde la audiencia del {origen.aud_fecha.isoformat()}" if origen.aud_fecha else "",
    )  # fmt: skip
