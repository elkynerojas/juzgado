import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def nuevo_id() -> str:
    return uuid.uuid4().hex


def ahora() -> datetime:
    # UTC sin zona: SQLite devuelve las fechas sin tzinfo y así se pueden comparar
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    es_sistema: Mapped[bool] = mapped_column(default=False)

    permisos: Mapped[list["RolPermiso"]] = relationship(cascade="all, delete-orphan", back_populates="rol")


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permiso: Mapped[str] = mapped_column(String(80), primary_key=True)

    rol: Mapped[Rol] = relationship(back_populates="permisos")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    activo: Mapped[bool] = mapped_column(default=True)
    preferencias: Mapped[dict] = mapped_column(JSON, default=dict)
    creado_en: Mapped[datetime] = mapped_column(default=ahora)
    ultimo_acceso: Mapped[datetime | None]

    rol: Mapped[Rol] = relationship()


class Sesion(Base):
    __tablename__ = "sesiones"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    creado_en: Mapped[datetime] = mapped_column(default=ahora)
    expira_en: Mapped[datetime]

    usuario: Mapped[Usuario] = relationship()


class _Rastreable:
    version: Mapped[int] = mapped_column(default=1)
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(default=ahora)
    actualizado_en: Mapped[datetime] = mapped_column(default=ahora, onupdate=ahora)


class Proceso(_Rastreable, Base):
    __tablename__ = "procesos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    radicado: Mapped[str] = mapped_column(String(60), index=True)
    naturaleza: Mapped[str] = mapped_column(String(40), default="Civil")
    clase: Mapped[str] = mapped_column(String(200), default="")
    demandante: Mapped[str] = mapped_column(String(300), default="")
    demandado: Mapped[str] = mapped_column(String(300), default="")
    fecha_rad: Mapped[date | None]
    situacion: Mapped[str] = mapped_column(String(40), default="Activo")
    macroetapa: Mapped[str] = mapped_column(String(120), default="")
    notas: Mapped[str] = mapped_column(Text, default="")

    actuaciones: Mapped[list["Actuacion"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, back_populates="proceso"
    )


class Actuacion(_Rastreable, Base):
    __tablename__ = "actuaciones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    proceso_id: Mapped[str] = mapped_column(ForeignKey("procesos.id", ondelete="CASCADE"), index=True)
    # cuaderno, materia, tipo y término van como texto: borrar una opción del catálogo no altera lo ya registrado
    cuaderno: Mapped[str] = mapped_column(String(120), default="Principal")
    materia: Mapped[str] = mapped_column(String(120), default="")
    tipo_solicitud: Mapped[str] = mapped_column(String(160), default="")
    origen: Mapped[str] = mapped_column(String(60), default="Memorial")
    descripcion: Mapped[str] = mapped_column(Text, default="")
    fecha_memorial: Mapped[date | None]
    constancia: Mapped[date | None]
    pasa: Mapped[str] = mapped_column(String(40), default="")
    pase: Mapped[date | None]
    providencia: Mapped[date | None]
    ejecutoria: Mapped[date | None]
    cumplida: Mapped[date | None]
    termino: Mapped[str] = mapped_column(String(200), default="")
    termino_dias: Mapped[int | None]
    termino_habil: Mapped[bool] = mapped_column(default=True)
    fecha_inicio: Mapped[date | None]
    suspende: Mapped[bool] = mapped_column(default=False)
    obs: Mapped[str] = mapped_column(Text, default="")
    ruta_id: Mapped[str] = mapped_column(String(32), default="")
    paso_idx: Mapped[int | None]

    proceso: Mapped[Proceso] = relationship(back_populates="actuaciones")


class Catalogo(Base):
    __tablename__ = "catalogos"
    __table_args__ = (UniqueConstraint("tipo", "valor"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    valor: Mapped[str] = mapped_column(String(200))
    orden: Mapped[int] = mapped_column(default=0)


class Termino(Base):
    __tablename__ = "terminos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True)
    dias: Mapped[int]
    habil: Mapped[bool] = mapped_column(default=True)
    responsable: Mapped[str] = mapped_column(String(80), default="")
    categoria: Mapped[str] = mapped_column(String(80), default="")
    orden: Mapped[int] = mapped_column(default=0)


class Ruta(Base):
    __tablename__ = "rutas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    orden: Mapped[int] = mapped_column(default=0)

    pasos: Mapped[list["RutaPaso"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="RutaPaso.orden", back_populates="ruta"
    )


class RutaPaso(Base):
    __tablename__ = "ruta_pasos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ruta_id: Mapped[str] = mapped_column(ForeignKey("rutas.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(default=0)
    nombre: Mapped[str] = mapped_column(String(200))
    materia: Mapped[str] = mapped_column(String(120), default="")
    origen: Mapped[str] = mapped_column(String(60), default="Memorial")
    termino: Mapped[str] = mapped_column(String(200), default="")
    descripcion: Mapped[str] = mapped_column(Text, default="")

    ruta: Mapped[Ruta] = relationship(back_populates="pasos")


class TipoRuta(Base):
    __tablename__ = "tipo_ruta"

    tipo_solicitud: Mapped[str] = mapped_column(String(160), primary_key=True)
    ruta_id: Mapped[str] = mapped_column(ForeignKey("rutas.id", ondelete="CASCADE"))


class Festivo(Base):
    __tablename__ = "festivos"

    fecha: Mapped[date] = mapped_column(primary_key=True)


class CalSuspension(Base):
    __tablename__ = "cal_suspensiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    desde: Mapped[date]
    hasta: Mapped[date]
    motivo: Mapped[str] = mapped_column(String(300), default="")


class CalDia(Base):
    __tablename__ = "cal_dias"

    CERRADO = "cerrado"
    REABIERTO = "reabierto"

    fecha: Mapped[date] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12), primary_key=True)


class Plantilla(Base):
    __tablename__ = "plantillas"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    tipo: Mapped[str] = mapped_column(String(40))
    nombre: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text, default="")


class Firmante(Base):
    __tablename__ = "firmantes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[str] = mapped_column(String(120), default="")
    firma: Mapped[bytes | None] = mapped_column(LargeBinary)
    firma_mime: Mapped[str] = mapped_column(String(40), default="")
    orden: Mapped[int] = mapped_column(default=0)


class Config(Base):
    __tablename__ = "config"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")
    binario: Mapped[bytes | None] = mapped_column(LargeBinary)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(default=ahora, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    usuario_nombre: Mapped[str] = mapped_column(String(160), default="")
    entidad: Mapped[str] = mapped_column(String(40), index=True)
    entidad_id: Mapped[str] = mapped_column(String(64), default="")
    accion: Mapped[str] = mapped_column(String(20))
    antes: Mapped[dict | None] = mapped_column(JSON)
    despues: Mapped[dict | None] = mapped_column(JSON)
