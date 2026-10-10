import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, StringConstraints, model_validator

from app.server.db.models import CalDia
from app.server.domain import audiencias as A
from app.server.domain import naturaleza as N
from app.server.domain import secretaria as S

# el frontend manda "" en los campos vacíos
Fecha = Annotated[date | None, BeforeValidator(lambda v: v or None)]
Texto = Annotated[str, BeforeValidator(lambda v: "" if v is None else v), StringConstraints(strip_whitespace=True)]
Requerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]
Entero = Annotated[Annotated[int, Field(ge=1)] | None, BeforeValidator(lambda v: v or None)]


def _hora(v) -> str:
    """Hora del día como "HH:MM"; cualquier cosa que no lo sea se descarta en vez de romper el guardado."""
    v = (v or "").strip()
    return v if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", v) else ""


Hora = Annotated[str, BeforeValidator(_hora)]


def _naturaleza(v):
    if not N.guardable(v):
        raise ValueError(f"Naturaleza no válida: {v!r}. La penal debe traer ley y procedimiento.")
    return v


Naturaleza = Annotated[Texto, AfterValidator(_naturaleza)]


class Instalacion(BaseModel):
    usuario: Requerido
    nombre: Requerido
    password: Password


class Login(BaseModel):
    usuario: str
    password: str


class CambioPassword(BaseModel):
    actual: str
    nueva: Password


class UsuarioNuevo(BaseModel):
    usuario: Requerido
    nombre: Requerido
    password: Password
    rol_id: int


class UsuarioEdicion(BaseModel):
    nombre: Requerido
    rol_id: int
    activo: bool
    password: Password | None = None


class RolIn(BaseModel):
    nombre: Requerido
    descripcion: Texto = ""
    permisos: list[str] = []


class SolicitudPenalIn(BaseModel):
    """Una solicitud de control de garantías. Se conserva el id para que los diffs de auditoría sean estables."""

    id: Texto = ""
    tipo: Texto = ""
    fecha: Fecha = None
    entrada: Texto = "Nueva solicitud"
    salida: Texto = ""
    fecha_salida: Fecha = None
    hora_salida: Hora = ""
    detalle_salida: Texto = ""


class ProcesoIn(BaseModel):
    """Solo columnas de `procesos`: lo que se le pasa tal cual al modelo."""

    radicado: Requerido
    naturaleza: Naturaleza = "Civil"
    clase: Texto = ""
    demandante: Texto = ""
    demandado: Texto = ""
    fecha_rad: Fecha = None
    situacion: Texto = "Activo"
    macroetapa: Texto = ""
    # estadística SIERJU
    tipo_sierju: Texto = ""
    via: Literal["Oral", "Escrito"] = "Oral"
    tipo_entrada: Texto = ""
    fecha_terminacion: Fecha = None
    fecha_archivo: Fecha = None
    forma_salida: Texto = ""
    tramite_posterior: bool = False
    fecha_tramite_posterior: Fecha = None
    # penal
    noticia_criminal: Texto = ""
    solicitud_penal: Texto = ""
    delitos_adicionales: list[Texto] = []
    # tutela
    impugnacion: Texto = ""
    fecha_impugnacion: Fecha = None
    decision_2da: Texto = ""
    medida_tutela: Texto = ""
    # incidente de desacato
    des_tutela: Texto = ""
    des_req: Fecha = None
    des_apertura: Texto = ""
    des_consulta: Texto = ""
    cuaderno_inicial: Texto = "Principal"
    cuadernos: list[Texto] = []

    def columnas(self) -> dict:
        return {k: getattr(self, k) for k in ProcesoIn.model_fields}


class ProcesoGuardado(ProcesoIn):
    """Lo que manda el formulario: las columnas más lo que el dominio necesita para los automatismos."""

    solicitudes_penales: list[SolicitudPenalIn] = []
    crear_inicial: bool = True
    crear_medidas: bool = False

    @model_validator(mode="after")
    def _revisar_solicitudes(self):
        if not N.es_garantias(self.naturaleza):
            self.solicitudes_penales = []
            return self
        if not self.solicitudes_penales:
            raise ValueError("Agregue al menos una solicitud de control de garantías.")
        for i, s in enumerate(self.solicitudes_penales, 1):
            if s.salida and not s.fecha_salida:
                raise ValueError(f"Indique la fecha de salida de la solicitud {i}.")
            if s.salida == N.SALIDA_NO_EFECTIVA and not s.detalle_salida:
                raise ValueError(f"Indique el motivo de la salida no efectiva de la solicitud {i}.")
        return self


class ProcesoEdicion(ProcesoGuardado):
    version: int


class NotasIn(BaseModel):
    notas: Texto = ""
    version: int


class ActuacionBase(BaseModel):
    cuaderno: Texto = "Principal"
    materia: Texto = ""
    tipo_solicitud: Texto = ""
    origen: Texto = "Memorial"
    descripcion: Texto = ""
    fecha_memorial: Fecha = None
    constancia: Fecha = None
    pasa: Texto = ""
    pase: Fecha = None
    providencia: Fecha = None
    ejecutoria: Fecha = None
    cumplida: Fecha = None
    termino: Texto = ""
    termino_dias: Entero = None
    termino_habil: bool = True
    fecha_inicio: Fecha = None
    suspende: bool = False
    obs: Texto = ""
    ruta_id: Texto = ""
    paso_idx: Annotated[int, Field(ge=0)] | None = None
    # trámite posterior, responsable y cierre
    tp_tipo: Texto = ""
    asignado_a: Texto = ""
    tipo_providencia: Texto = ""
    modo_cierre: Literal[*S.MODOS_CIERRE] = ""  # type: ignore[valid-type]
    salida_stat: Texto = ""
    entrada_stat: Texto = ""
    # audiencia
    es_audiencia: bool = False
    aud_fecha: Fecha = None
    aud_hora: Hora = ""
    aud_estado: Texto = ""
    aud_tipo: Texto = ""
    aud_causa: Texto = ""
    aud_inmediata: bool = False
    # recursos y resultado en el superior
    recurso_tipo: Texto = ""
    recurso_fecha: Fecha = None
    recurso_objeto: Texto = ""
    rec_traslado: Fecha = None
    superior_resultado: Texto = ""
    superior_fecha: Fecha = None
    rec_impug: Texto = ""
    rec_impug_result: Texto = ""
    rec_impug_fecha: Fecha = None
    # remate y amparo de pobreza
    remate_realizado: bool = False
    amparo_pobreza_concedido: bool = False
    # notificación y ejecutoria
    notif_fecha: Fecha = None
    notif_forma: Texto = ""
    ejec_dias: Annotated[int, Field(ge=1)] = S.EJEC_DIAS

    @model_validator(mode="after")
    def _revisar_audiencia(self):
        if not self.es_audiencia:
            # desmarcar la casilla limpia la audiencia: si no, quedarían fecha y estado huérfanos contando en SIERJU
            self.aud_fecha = None
            self.aud_hora = self.aud_estado = self.aud_tipo = self.aud_causa = ""
            self.aud_inmediata = False
            return self
        if self.aud_estado and self.aud_estado not in A.ESTADOS:
            raise ValueError(f"Estado de audiencia no válido: {self.aud_estado!r}")
        if not A.lleva_causa(self.aud_estado):
            self.aud_causa = ""
        return self


class ActuacionIn(ActuacionBase):
    descripcion: Requerido


class ActuacionEdicion(ActuacionIn):
    version: int


class ValorIn(BaseModel):
    valor: Requerido


class TerminoIn(BaseModel):
    nombre: Requerido
    dias: int = Field(ge=1)
    habil: bool = True
    responsable: Texto = ""
    categoria: Texto = ""


class RutaIn(BaseModel):
    nombre: Requerido
    descripcion: Texto = ""


class PasoIn(BaseModel):
    nombre: Requerido
    materia: Texto = ""
    origen: Texto = "Memorial"
    termino: Texto = ""
    descripcion: Texto = ""
    # sin estos dos, editar un paso borraba la marca de audiencia y desarmaba la ruta de control de garantías
    es_audiencia: bool = False
    aud_estado: Texto = ""


class PersonalIn(BaseModel):
    nombre: Requerido
    cargo: Texto = ""
    activo: bool = True


class AudienciaIn(BaseModel):
    proceso_id: Requerido
    cuaderno: Texto = ""
    fecha: date
    hora: Hora = ""
    tipo: Texto = ""
    estado: Texto = A.PROGRAMADA
    causa: Texto = ""
    asignado_a: Texto = ""


class ResolverIn(BaseModel):
    version: int
    estado: Texto
    causa: Texto = ""
    # si se fijó otra audiencia en la diligencia
    nueva_fecha: Fecha = None
    nueva_hora: Hora = ""
    nuevo_tipo: Texto = ""


class TipoRutaIn(BaseModel):
    tipo_solicitud: Requerido
    ruta_id: str | None = None


class SuspensionIn(BaseModel):
    desde: date
    hasta: date
    motivo: Texto = ""


class DiaIn(BaseModel):
    fecha: date
    tipo: Literal[CalDia.CERRADO, CalDia.REABIERTO]


class FestivoIn(BaseModel):
    fecha: date


class PlantillaIn(BaseModel):
    nombre: Requerido
    tipo: Literal["Constancia", "Pase al despacho"]
    cuerpo: str = ""


class FirmanteIn(BaseModel):
    nombre: Requerido
    cargo: Texto = ""


class JuzgadoIn(BaseModel):
    juzgado: Texto = ""
    ciudad: Texto = ""
    prefijo: Texto = ""


class DocTextoIn(BaseModel):
    plantilla_id: str
    motivo: Texto = ""
    fecha: Fecha = None


class DocHtmlIn(BaseModel):
    cuerpo: str
    fecha: Fecha = None
    firmante_id: str | None = None


class StatEventoIn(BaseModel):
    """Un dato que no nace de ninguna actuación: caracterización de partes, turnos, variables especiales."""

    fecha: date
    seccion: Requerido
    fila: Requerido
    columna: Requerido
    cantidad: Annotated[int, Field(ge=1)] = 1
    proceso_id: Texto = ""
    nota: Texto = ""
