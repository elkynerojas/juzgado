from datetime import date

from sqlalchemy import func, inspect, select

from app.server.db import models as m
from app.server.db.seeds import cargar_catalogos, sembrar

ESPERADAS = {
    "actuaciones", "auditoria", "cal_dias", "cal_suspensiones", "catalogos", "config", "festivos", "firmantes",
    "plantillas", "procesos", "rol_permisos", "roles", "ruta_pasos", "rutas", "sesiones", "terminos", "tipo_ruta",
    "usuarios", "personal", "proceso_solicitudes_penales", "stat_eventos",
}  # fmt: skip


def contar(s, modelo):
    return s.scalar(select(func.count()).select_from(modelo))


def test_migracion_crea_el_esquema_del_modelo(sesion):
    tablas = set(inspect(sesion.get_bind()).get_table_names())
    assert ESPERADAS <= tablas
    assert set(m.Base.metadata.tables) == ESPERADAS


def test_pragmas(sesion):
    assert sesion.connection().exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    assert sesion.connection().exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"


def test_semillas_una_sola_vez(sesion):
    d = cargar_catalogos()
    assert sembrar(sesion) is True
    assert sembrar(sesion) is False
    assert contar(sesion, m.Festivo) == len(d["festivos"]) == 91
    assert contar(sesion, m.Termino) == len(d["terminos"]) == 49
    assert contar(sesion, m.Ruta) == 7
    assert contar(sesion, m.Plantilla) == 7
    assert contar(sesion, m.TipoRuta) == len(d["tipoRuta"])
    tipos = dict(sesion.execute(select(m.Catalogo.tipo, func.count()).group_by(m.Catalogo.tipo)).all())
    assert tipos == {
        "materias": 23, "tipos_solicitud": 69, "cuadernos": 24, "macroetapas": 17,
        "asuntos_civil": 56, "asuntos_familia": 33, "cargos": 5,
    }  # fmt: skip
    ruta = sesion.get(m.Ruta, "r_traslado")
    assert [p.nombre for p in ruta.pasos] == ["Correr traslado", "Resolver (decisión del despacho)", "Ejecutoria y notificación"]
    assert sesion.get(m.Config, "prefijo").valor == "54-172-40-89-001-"
    assert sesion.get(m.Config, "membrete").binario.startswith(b"\x89PNG")
    assert sesion.scalars(select(m.Firmante)).one().firma.startswith(b"\x89PNG")


def test_borrar_proceso_borra_sus_actuaciones(sesion):
    p = m.Proceso(radicado="2026-00001")
    p.actuaciones = [m.Actuacion(descripcion="a", fecha_memorial=date(2026, 9, 1)), m.Actuacion(descripcion="b")]
    sesion.add(p)
    sesion.commit()
    assert p.version == 1 and len(p.id) == 32 and p.situacion == "Activo"
    assert contar(sesion, m.Actuacion) == 2
    # borrado directo en SQL: debe actuar el ON DELETE CASCADE de la base, no el ORM
    sesion.execute(m.Proceso.__table__.delete().where(m.Proceso.id == p.id))
    sesion.commit()
    assert contar(sesion, m.Actuacion) == 0
