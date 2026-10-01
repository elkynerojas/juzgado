from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.server.db.models import CalDia

# el frontend manda "" en los campos vacíos
Fecha = Annotated[date | None, BeforeValidator(lambda v: v or None)]
Texto = Annotated[str, BeforeValidator(lambda v: "" if v is None else v), StringConstraints(strip_whitespace=True)]
Requerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]


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


class ProcesoIn(BaseModel):
    radicado: Requerido
    naturaleza: Texto = "Civil"
    clase: Texto = ""
    demandante: Texto = ""
    demandado: Texto = ""
    fecha_rad: Fecha = None
    situacion: Texto = "Activo"
    macroetapa: Texto = ""


class ProcesoEdicion(ProcesoIn):
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
    termino_dias: Annotated[Annotated[int, Field(ge=1)] | None, BeforeValidator(lambda v: v or None)] = None
    termino_habil: bool = True
    fecha_inicio: Fecha = None
    suspende: bool = False
    obs: Texto = ""
    ruta_id: Texto = ""
    paso_idx: Annotated[int, Field(ge=0)] | None = None


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
