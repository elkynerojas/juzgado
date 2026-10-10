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
    # estadística SIERJU: tipo de proceso (o delito / derecho invocado), vía, ingreso y salida
    tipo_sierju: Mapped[str] = mapped_column(String(300), default="")
    via: Mapped[str] = mapped_column(String(20), default="Oral")
    tipo_entrada: Mapped[str] = mapped_column(String(200), default="")
    fecha_terminacion: Mapped[date | None]
    fecha_archivo: Mapped[date | None]
    forma_salida: Mapped[str] = mapped_column(String(200), default="")
    tramite_posterior: Mapped[bool] = mapped_column(default=False)
    fecha_tramite_posterior: Mapped[date | None]
    # penal
    noticia_criminal: Mapped[str] = mapped_column(String(60), default="")
    solicitud_penal: Mapped[str] = mapped_column(String(300), default="")
    delitos_adicionales: Mapped[list] = mapped_column(JSON, default=list)
    # tutela
    impugnacion: Mapped[str] = mapped_column(String(10), default="")
    fecha_impugnacion: Mapped[date | None]
    decision_2da: Mapped[str] = mapped_column(String(200), default="")
    medida_tutela: Mapped[str] = mapped_column(String(10), default="")
    # incidente de desacato
    des_tutela: Mapped[str] = mapped_column(String(60), default="")
    des_req: Mapped[date | None]
    des_apertura: Mapped[str] = mapped_column(String(40), default="")
    des_consulta: Mapped[str] = mapped_column(String(40), default="")
    cuaderno_inicial: Mapped[str] = mapped_column(String(120), default="Principal")
    # cuadernos abiertos aunque todavía no tengan actuaciones
    cuadernos: Mapped[list] = mapped_column(JSON, default=list)

    actuaciones: Mapped[list["Actuacion"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, back_populates="proceso"
    )
    solicitudes_penales: Mapped[list["SolicitudPenal"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="SolicitudPenal.orden", back_populates="proceso"
    )


class SolicitudPenal(Base):
    """Cada solicitud de control de garantías radicada en un proceso penal."""

    __tablename__ = "proceso_solicitudes_penales"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    proceso_id: Mapped[str] = mapped_column(ForeignKey("procesos.id", ondelete="CASCADE"), index=True)
    orden: Mapped[int] = mapped_column(default=0)
    tipo: Mapped[str] = mapped_column(String(300), default="")
    fecha: Mapped[date | None]
    entrada: Mapped[str] = mapped_column(String(60), default="Nueva solicitud")
    salida: Mapped[str] = mapped_column(String(60), default="")
    fecha_salida: Mapped[date | None]
    hora_salida: Mapped[str] = mapped_column(String(5), default="")
    detalle_salida: Mapped[str] = mapped_column(String(300), default="")

    proceso: Mapped[Proceso] = relationship(back_populates="solicitudes_penales")


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
    tp_tipo: Mapped[str] = mapped_column(String(120), default="")
    asignado_a: Mapped[str] = mapped_column(String(200), default="")
    tipo_providencia: Mapped[str] = mapped_column(String(40), default="")
    modo_cierre: Mapped[str] = mapped_column(String(40), default="")
    salida_stat: Mapped[str] = mapped_column(String(200), default="")
    entrada_stat: Mapped[str] = mapped_column(String(200), default="")
    # audiencia
    es_audiencia: Mapped[bool] = mapped_column(default=False)
    aud_fecha: Mapped[date | None]
    aud_hora: Mapped[str] = mapped_column(String(5), default="")
    aud_estado: Mapped[str] = mapped_column(String(40), default="")
    aud_tipo: Mapped[str] = mapped_column(String(200), default="")
    aud_causa: Mapped[str] = mapped_column(String(300), default="")
    aud_inmediata: Mapped[bool] = mapped_column(default=False)
    # audiencia que esta actuación da por cancelada (gestión automática de garantías)
    cancelacion_de: Mapped[str] = mapped_column(String(32), default="")
    # recursos
    recurso_tipo: Mapped[str] = mapped_column(String(40), default="")
    recurso_fecha: Mapped[date | None]
    recurso_objeto: Mapped[str] = mapped_column(String(20), default="")
    rec_traslado: Mapped[date | None]
    superior_resultado: Mapped[str] = mapped_column(String(200), default="")
    superior_fecha: Mapped[date | None]
    rec_impug: Mapped[str] = mapped_column(String(5), default="")
    rec_impug_result: Mapped[str] = mapped_column(String(200), default="")
    rec_impug_fecha: Mapped[date | None]
    remate_realizado: Mapped[bool] = mapped_column(default=False)
    amparo_pobreza_concedido: Mapped[bool] = mapped_column(default=False)
    # notificación y ejecutoria
    notif_fecha: Mapped[date | None]
    notif_forma: Mapped[str] = mapped_column(String(40), default="")
    ejec_dias: Mapped[int] = mapped_column(default=3)

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
    es_audiencia: Mapped[bool] = mapped_column(default=False)
    aud_estado: Mapped[str] = mapped_column(String(40), default="")

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


class Personal(Base):
    """Personal del despacho al que se asignan actuaciones y audiencias; no son usuarios del sistema."""

    __tablename__ = "personal"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(200))
    cargo: Mapped[str] = mapped_column(String(120), default="")
    activo: Mapped[bool] = mapped_column(default=True)


class StatEvento(Base):
    """Dato estadístico SIERJU registrado a mano (los automáticos se calculan, no se guardan)."""

    __tablename__ = "stat_eventos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    fecha: Mapped[date] = mapped_column(index=True)
    seccion: Mapped[str] = mapped_column(String(20))
    fila: Mapped[str] = mapped_column(Text)
    columna: Mapped[str] = mapped_column(Text)
    cantidad: Mapped[int] = mapped_column(default=1)
    proceso_id: Mapped[str | None] = mapped_column(ForeignKey("procesos.id", ondelete="SET NULL"))
    nota: Mapped[str] = mapped_column(Text, default="")
    creado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    creado_en: Mapped[datetime] = mapped_column(default=ahora)


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
