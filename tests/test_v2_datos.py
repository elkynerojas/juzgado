"""Fase 7: modelo de la v2 del HTML (penal, constitucionales, audiencias, SIERJU, personal)."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.server.db.migrate import MIGRATIONS_DIR, actualizar
from app.server.db.session import crear_engine
from tests.conftest import golden
from tests.test_api_respaldo import estado


def test_restaurar_respaldo_del_html_v2(admin):
    legacy = golden("respaldo_legacy_v2.json")
    r = admin.post("/api/respaldo/restaurar", json=legacy)
    assert r.status_code == 200, r.text
    assert r.json()["procesos"] == 10 and r.json()["stat_eventos"] == 2  # el evento sin fecha se descarta

    exp = admin.get("/api/respaldo").json()
    procesos = {p["id"]: p for p in exp["procesos"]}
    pg = procesos["pg"]
    assert pg["naturaleza"] == "Penal 906 - Garantías" and pg["noticia_criminal"] == "541726000000202600123"
    assert pg["delitos_adicionales"] == ["ARTÍCULO 111. LESIONES DOLOSAS"] and pg["cuadernos"] == ["Principal"]
    s1, s2 = pg["solicitudes_penales"]
    assert s1 | {"id": "", "orden": 0} == {
        "id": "", "orden": 0, "tipo": "LEGALIZACIÓN DE CAPTURA", "fecha": "2026-09-01", "entrada": "Nueva solicitud",
        "salida": "Autos decisiones de fondo", "fecha_salida": "2026-09-02", "hora_salida": "10:30", "detalle_salida": "",
    }  # fmt: skip
    assert (s2["id"], s2["orden"], s2["entrada"], s2["fecha_salida"]) == ("s2", 1, "Reingreso", None)
    # una solicitud única de respaldos anteriores a la lista pasa a ser la primera de la lista
    [unica] = procesos["pv"]["solicitudes_penales"]
    assert (unica["tipo"], unica["fecha"]) == ("LEGALIZACIÓN DE CAPTURA", "2026-09-01")

    pt = procesos["pt"]
    assert (pt["fecha_terminacion"], pt["forma_salida"], pt["impugnacion"], pt["fecha_impugnacion"]) == ("2026-09-15", "Concede", "Sí", "2026-09-18")
    assert (pt["decision_2da"], pt["medida_tutela"], pt["cuadernos"]) == ("Confirma", "Sí", ["Principal", "Incidente de desacato 1"])
    pd = procesos["pd"]
    assert (pd["des_tutela"], pd["des_req"], pd["des_apertura"], pd["des_consulta"]) == ("2026-00101", "2026-09-20", "Apertura", "Confirma")
    assert pd["tramite_posterior"] is True and pd["fecha_tramite_posterior"] == "2026-09-25"
    # campos que el HTML viejo no tenía toman su valor por defecto
    viejo = next(p for p in exp["procesos"] if p["id"] not in {"pg", "pt", "pd", "pv"})
    assert (viejo["via"], viejo["cuaderno_inicial"], viejo["cuadernos"], viejo["solicitudes_penales"]) == ("Oral", "Principal", [], [])

    acts = {a["id"]: a for a in exp["actuaciones"]}
    aa, ab = acts["aa"], acts["ab"]
    assert (aa["es_audiencia"], aa["aud_fecha"], aa["aud_hora"], aa["aud_estado"], aa["aud_inmediata"]) == (True, "2026-09-03", "09:00", "Aplazada", True)
    assert (aa["aud_causa"], aa["asignado_a"], aa["modo_cierre"], aa["ejec_dias"]) == (
        "Inasistencia del fiscal o acusador privado", "ANA RUIZ (Oficial Mayor)", "Providencia", 3,
    )  # fmt: skip
    assert (ab["recurso_tipo"], ab["rec_traslado"], ab["superior_resultado"], ab["rec_impug_fecha"]) == ("Impugnación", "2026-09-19", "Revocan", "2026-10-05")
    assert (ab["remate_realizado"], ab["amparo_pobreza_concedido"], ab["notif_forma"], ab["ejec_dias"]) == (True, True, "Personal / electrónica", 5)
    assert (ab["tp_tipo"], ab["salida_stat"], ab["entrada_stat"], ab["cancelacion_de"]) == ("Remates", "Concede", "Acción de tutela", "aa")

    eventos = exp["stat_eventos"]
    assert [(e["seccion"], e["cantidad"], e["proceso_id"]) for e in eventos] == [("SEC4416", 2, "pt"), ("SEC3746", 1, None)]
    assert eventos[0]["nota"] == "registro a mano"

    cfg = exp["config"]
    assert [(x["nombre"], x["cargo"], x["activo"]) for x in cfg["personal"]] == [("ANA RUIZ", "Oficial Mayor", True), ("LUIS PAZ", "Citador", True)]
    assert cfg["catalogos"]["cargos"][-1] == "Notificador" and "Incidente de desacato" in cfg["catalogos"]["cuadernos"]
    garantias = next(r for r in cfg["rutas"] if r["id"] == "r_garantias")
    assert [(p["es_audiencia"], p["aud_estado"]) for p in garantias["pasos"]] == [(False, ""), (True, "Programada"), (True, "Realizada")]


def test_respaldo_v4_ida_y_vuelta(admin):
    assert admin.post("/api/respaldo/restaurar", json=golden("respaldo_legacy_v2.json")).status_code == 200
    respaldo = admin.get("/api/respaldo").json()
    assert respaldo["version"] == 4
    antes = estado(admin)

    admin.post("/api/datos/vaciar")
    assert admin.post("/api/respaldo/restaurar", json=golden("respaldo_legacy.json")).status_code == 200
    assert estado(admin) != antes
    r = admin.post("/api/respaldo/restaurar", json=respaldo)
    assert r.status_code == 200, r.text
    assert estado(admin) == antes


def test_vaciar_borra_eventos_y_conserva_personal(admin):
    assert admin.post("/api/respaldo/restaurar", json=golden("respaldo_legacy_v2.json")).status_code == 200
    admin.post("/api/datos/vaciar")
    exp = admin.get("/api/respaldo").json()
    assert exp["procesos"] == [] and exp["stat_eventos"] == [] and len(exp["config"]["personal"]) == 2


def test_respaldo_v3_sigue_siendo_valido(admin):
    admin.post("/api/datos/ejemplos")
    v3 = admin.get("/api/respaldo").json() | {"version": 3}
    v3.pop("stat_eventos")
    v3["config"].pop("personal")
    for p in v3["procesos"]:
        for k in ("solicitudes_penales", "tipo_sierju", "via", "cuadernos", "delitos_adicionales"):
            p.pop(k)
    r = admin.post("/api/respaldo/restaurar", json=v3)
    assert r.status_code == 200, r.text
    assert {p["via"] for p in admin.get("/api/respaldo").json()["procesos"]} == {"Oral"}


def _alembic(engine, destino: str, accion=command.upgrade) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.begin() as con:
        cfg.attributes["connection"] = con
        accion(cfg, destino)


def test_migracion_0002_sobre_una_bd_de_la_version_anterior(tmp_path):
    engine = crear_engine(tmp_path / "vieja.db")
    _alembic(engine, "0001")
    with engine.begin() as con:
        sql = [
            "INSERT INTO config (clave, valor) VALUES ('semilla', '1')",
            "INSERT INTO catalogos (tipo, valor, orden) VALUES ('tipos_solicitud', 'Memorial', 0), ('cuadernos', 'Principal', 0)",
            "INSERT INTO rutas (id, nombre, descripcion, orden) VALUES ('r_traslado', 'Traslado', '', 0)",
            "INSERT INTO roles (id, nombre, descripcion, es_sistema) VALUES (1, 'Consulta', '', 0), (2, 'Propio', '', 0)",
            "INSERT INTO rol_permisos (rol_id, permiso) VALUES (1, 'procesos.ver')",
            "INSERT INTO procesos (id, radicado, naturaleza, clase, demandante, demandado, situacion, macroetapa, notas,"
            " version, creado_en, actualizado_en) VALUES ('p1', '2026-1', 'Civil', '', '', '', 'Activo', '', '', 1,"
            " '2026-01-01', '2026-01-01')",
            "INSERT INTO actuaciones (id, proceso_id, cuaderno, materia, tipo_solicitud, origen, descripcion, pasa, termino,"
            " termino_habil, suspende, obs, ruta_id, version, creado_en, actualizado_en) VALUES ('a1', 'p1', 'Principal',"
            " '', '', 'Memorial', 'x', '', '', 1, 0, '', '', 1, '2026-01-01', '2026-01-01')",
        ]
        for q in sql:
            con.execute(text(q))

    actualizar(engine)
    actualizar(engine)  # idempotente

    with engine.connect() as con:
        def filas(q):
            return con.execute(text(q)).all()

        # agregar columnas no recrea tablas: la actuación sobrevive (ON DELETE CASCADE no se dispara)
        assert filas("SELECT id, ejec_dias, es_audiencia, aud_hora FROM actuaciones") == [("a1", 3, 0, "")]
        assert filas("SELECT via, cuaderno_inicial, cuadernos, delitos_adicionales FROM procesos") == [("Oral", "Principal", "[]", "[]")]
        assert filas("SELECT valor FROM catalogos WHERE tipo = 'tipos_solicitud' ORDER BY orden") == [("Demanda",), ("Memorial",)]
        assert filas("SELECT valor FROM catalogos WHERE tipo = 'cuadernos' ORDER BY orden") == [("Principal",), ("Incidente de desacato",)]
        assert len(filas("SELECT 1 FROM catalogos WHERE tipo = 'cargos'")) == 5
        assert filas("SELECT id FROM rutas ORDER BY orden") == [("r_garantias",), ("r_traslado",)]
        assert filas("SELECT es_audiencia, aud_estado FROM ruta_pasos WHERE ruta_id = 'r_garantias' ORDER BY orden") == [
            (0, ""), (1, "Programada"), (1, "Realizada"),
        ]  # fmt: skip
        assert {p for (p,) in filas("SELECT permiso FROM rol_permisos WHERE rol_id = 1")} == {
            "procesos.ver", "audiencias.ver", "estadistica.ver",
        }  # fmt: skip
        assert filas("SELECT permiso FROM rol_permisos WHERE rol_id = 2") == []

    _alembic(engine, "0001", command.downgrade)
    with engine.connect() as con:
        assert con.execute(text("SELECT id FROM actuaciones")).all() == [("a1",)]
    engine.dispose()


def test_bd_nueva_no_duplica_lo_que_agrega_la_migracion(app, admin):
    c = admin.get("/api/config").json()
    tipos = [x["valor"] for x in c["catalogos"]["tipos_solicitud"]]
    assert tipos.count("Demanda") == 1 and tipos[0] == "Demanda"
    assert [r["id"] for r in c["rutas"]].count("r_garantias") == 1
    assert [x["valor"] for x in c["catalogos"]["cargos"]] == ["Juez", "Secretario", "Oficial Mayor", "Escribiente", "Citador"]


def test_completa_el_tipo_sierju_de_procesos_viejos(admin):
    assert admin.post("/api/respaldo/restaurar", json=golden("respaldo_legacy.json")).status_code == 200
    tipos = {p["clase"]: p["tipo_sierju"] for p in admin.get("/api/respaldo").json()["procesos"]}
    assert tipos["Ejecutivo singular"] == "Ejecutivos" and "" not in tipos.values()
    admin.post("/api/datos/ejemplos")
    assert all(p["tipo_sierju"] for p in admin.get("/api/respaldo").json()["procesos"])
    # uno ya clasificado a mano no se toca
    legacy = golden("respaldo_legacy_v2.json")
    assert admin.post("/api/respaldo/restaurar", json=legacy).status_code == 200
    pg = next(p for p in admin.get("/api/respaldo").json()["procesos"] if p["id"] == "pg")
    assert pg["tipo_sierju"] == "ARTÍCULO 239. HURTO"
