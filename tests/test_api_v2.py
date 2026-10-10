"""Los campos y automatismos de la v2 a través de la API (fase 9)."""

from app.server.db.seeds import cargar_sierju

GARANTIAS = {
    "radicado": "2026-00500",
    "naturaleza": "Penal 906 - Garantías",
    "fecha_rad": "2026-03-02",
    "noticia_criminal": "540016000000202600123",
    "tipo_sierju": "ARTÍCULO 239. HURTO",
}
SOL = {"tipo": "Legalización de captura", "fecha": "2026-03-02", "entrada": "Nueva solicitud"}


def _sols(p: dict) -> list[dict]:
    return p["solicitudes_penales"]


def test_naturaleza_penal_debe_traer_ley_y_procedimiento(admin):
    assert admin.post("/api/procesos", json={"radicado": "x", "naturaleza": "Penal"}).status_code == 422
    r = admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL]})
    assert r.status_code == 201, r.text
    assert r.json()["naturaleza"] == "Penal 906 - Garantías"


def test_garantias_exige_solicitudes_y_crea_su_gestion(admin):
    # sin solicitudes no se puede guardar un proceso de garantías
    assert admin.post("/api/procesos", json=GARANTIAS).status_code == 422
    # una salida sin fecha, o no efectiva sin motivo, tampoco
    assert admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL | {"salida": "Procesos acumulados"}]}).status_code == 422

    p = admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL, SOL | {"tipo": "Imputación"}]}).json()
    # en penal la clase del proceso es el delito, y la salida se lleva por solicitud
    assert p["clase"] == "ARTÍCULO 239. HURTO" and p["forma_salida"] == ""
    assert [s["tipo"] for s in _sols(p)] == ["Legalización de captura", "Imputación"]
    assert [s["orden"] for s in _sols(p)] == [0, 1]
    assert p["solicitud_penal"] == "Legalización de captura" and p["cuadernos"] == ["Principal"]

    # una sola actuación de radicación para las dos solicitudes, con la compuerta de secretaría ya resuelta
    assert len(p["actuaciones"]) == 1
    a = p["actuaciones"][0]
    assert a["ruta_id"] == "r_garantias" and a["paso_idx"] == 0
    assert "2 solicitudes de control de garantías" in a["descripcion"]
    assert a["constancia"] and a["pase"] and a["pasa"] == "Sí"

    # auditoría: el proceso y la actuación que nació sola
    aud = [x for x in admin.get("/api/auditoria").json()["filas"] if x["entidad"] in ("proceso", "actuacion")]
    assert [(x["entidad"], x["accion"]) for x in aud] == [("actuacion", "crear"), ("proceso", "crear")]
    assert next(x for x in aud if x["entidad"] == "actuacion")["entidad_id"] == a["id"]


def test_la_audiencia_se_cancela_cuando_las_solicitudes_salen_antes(admin):
    p = admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL]}).json()
    pid = p["id"]
    # se fija la audiencia (paso 1 de la ruta de garantías)
    admin.post(
        f"/api/procesos/{pid}/actuaciones",
        json={
            "descripcion": "Se fija audiencia de legalización",
            "cuaderno": "Principal",
            "ruta_id": "r_garantias",
            "paso_idx": 1,
            "es_audiencia": True,
            "aud_fecha": "2026-03-20",
            "aud_hora": "09:00",
            "aud_estado": "Programada",
        },
    )
    # la solicitud termina antes de la audiencia: la cancelación se registra sola al guardar el proceso
    cerrada = SOL | {
        "salida": "Otras salidas no efectivas",
        "fecha_salida": "2026-03-10",
        "hora_salida": "10:30",
        "detalle_salida": "Retiro de la solicitud por la Fiscalía",
    }
    d = admin.put(f"/api/procesos/{pid}", json=GARANTIAS | {"solicitudes_penales": [cerrada], "version": p["version"]}).json()

    cancelacion = next(a for a in d["actuaciones"] if a["aud_estado"] == "Cancelada / no realizada")
    assert cancelacion["aud_fecha"] == "2026-03-20" and cancelacion["aud_hora"] == "09:00"
    assert cancelacion["cancelacion_de"] == next(a["id"] for a in d["actuaciones"] if a["aud_estado"] == "Programada")
    # la causa tiene que ser una columna SIERJU real: la v2 guardaba etiquetas que no contaban
    causas = cargar_sierju()["audiencias"]["columnas_causa"]["penal_cancelada"]
    assert cancelacion["aud_causa"] == "Retiro de la solicitud por el fiscal"
    assert cancelacion["aud_causa"] in causas


def test_actuacion_inicial_por_naturaleza(admin):
    tutela = admin.post("/api/procesos", json={"radicado": "2026-00600", "naturaleza": "Tutela", "fecha_rad": "2026-03-02"}).json()
    a = tutela["actuaciones"][0]
    assert a["tipo_solicitud"] == "Acción de tutela" and a["termino_dias"] == 10 and a["termino_habil"] is True
    assert a["fecha_inicio"] == "2026-03-02"

    # sin fecha de radicación no hay de dónde partir, así que no se crea nada
    sin_fecha = admin.post("/api/procesos", json={"radicado": "2026-00601", "naturaleza": "Civil"}).json()
    assert sin_fecha["actuaciones"] == []
    # y se puede pedir que no se cree
    sin_pedir = admin.post(
        "/api/procesos", json={"radicado": "2026-00602", "naturaleza": "Civil", "fecha_rad": "2026-03-02", "crear_inicial": False}
    ).json()
    assert sin_pedir["actuaciones"] == []


def test_normaliza_fechas_y_cuadernos(admin):
    p = admin.post(
        "/api/procesos",
        json={
            "radicado": "2026-00700",
            "naturaleza": "Civil",
            "fecha_rad": "2026-01-10",
            "situacion": "Terminado",
            "tramite_posterior": True,
            "crear_medidas": True,
            "cuaderno_inicial": "Principal",
        },
    ).json()
    assert p["fecha_terminacion"] and p["fecha_tramite_posterior"] == p["fecha_terminacion"]
    assert p["cuadernos"] == ["Principal", "Medidas cautelares"]

    archivado = admin.post(
        "/api/procesos", json={"radicado": "2026-00701", "naturaleza": "Civil", "situacion": "Archivado"}
    ).json()
    assert archivado["fecha_archivo"] and archivado["fecha_terminacion"] is None


def test_audiencia_y_ejecutoria_en_la_actuacion(admin):
    pid = admin.post("/api/procesos", json={"radicado": "2026-00800", "naturaleza": "Civil"}).json()["id"]
    base = f"/api/procesos/{pid}/actuaciones"

    # desmarcar la audiencia limpia sus campos, para que no queden contando en la estadística
    a = admin.post(base, json={"descripcion": "No es audiencia", "es_audiencia": False, "aud_fecha": "2026-04-01", "aud_estado": "Aplazada"}).json()
    assert a["aud_fecha"] is None and a["aud_estado"] == "" and a["aud_causa"] == ""
    # un estado que no aplaza ni cancela no lleva causa
    a = admin.post(base, json={"descripcion": "Audiencia", "es_audiencia": True, "aud_fecha": "2026-04-01", "aud_estado": "Realizada", "aud_causa": "Lo que sea"}).json()
    assert a["aud_causa"] == ""
    assert admin.post(base, json={"descripcion": "x", "es_audiencia": True, "aud_estado": "Inventada"}).status_code == 422

    # la ejecutoria se calcula con la notificación; un recurso sin resolver la suspende
    a = admin.post(base, json={"descripcion": "Auto", "providencia": "2026-04-01", "notif_fecha": "2026-04-02", "ejec_dias": 3}).json()
    assert a["ejecutoria"] and a["derivado"]["ejecutoria_estado"]["estado"] == "corre"
    datos = {k: a[k] for k in a if k not in ("derivado", "siguiente", "id", "proceso_id")}
    a = admin.put(f"/api/actuaciones/{a['id']}", json=datos | {"ejecutoria": "", "recurso_tipo": "Apelación", "recurso_fecha": "2026-04-03"}).json()
    assert a["derivado"]["ejecutoria_estado"] == {"estado": "suspendida", "fecha": None, "pendiente": "superior"}
    assert a["ejecutoria"] is None


def test_el_paso_de_la_ruta_conserva_la_marca_de_audiencia(admin):
    """Editar un paso borraba es_audiencia y desarmaba la ruta de control de garantías."""
    ruta = next(x for x in admin.get("/api/config").json()["rutas"] if x["id"] == "r_garantias")
    paso = next(p for p in ruta["pasos"] if p["es_audiencia"])
    r = admin.put(f"/api/config/pasos/{paso['id']}", json={k: paso[k] for k in paso if k != "id"})
    assert r.status_code == 200, r.text
    ruta = next(x for x in admin.get("/api/config").json()["rutas"] if x["id"] == "r_garantias")
    assert next(p for p in ruta["pasos"] if p["id"] == paso["id"])["es_audiencia"] is True


def test_consulta_no_puede_escribir_los_campos_nuevos(admin, crear_usuario):
    consulta = crear_usuario("lector", "Consulta")
    assert consulta.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL]}).status_code == 403
    pid = admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL]}).json()["id"]
    assert consulta.get(f"/api/procesos/{pid}").status_code == 200
    assert consulta.put(f"/api/procesos/{pid}", json=GARANTIAS | {"solicitudes_penales": [SOL], "version": 1}).status_code == 403


def test_cui_y_naturaleza_en_los_documentos(admin):
    p = admin.post("/api/procesos", json=GARANTIAS | {"solicitudes_penales": [SOL]}).json()
    tpl = admin.post(
        "/api/config/plantillas",
        json={"nombre": "Con CUI", "tipo": "Constancia", "cuerpo": "CUI {{cui}} · {{naturaleza}} · {{tipo_sierju}}"},
    ).json()
    aid = p["actuaciones"][0]["id"]
    texto = admin.post(f"/api/actuaciones/{aid}/documento/texto", json={"plantilla_id": tpl["id"]})
    assert texto.status_code == 200, texto.text
    assert texto.json()["cuerpo"] == "CUI 540016000000202600123 · Penal 906 - Garantías · ARTÍCULO 239. HURTO"


def test_los_ejemplos_alimentan_audiencias_y_estadistica(admin):
    """Regresión viva de las cuatro fases: los ejemplos deben mover todo lo nuevo."""
    from datetime import date, timedelta

    assert admin.post("/api/datos/ejemplos").json() == {"procesos": 12, "actuaciones": 27}

    # los ejemplos traen las naturalezas nuevas
    filas = admin.get("/api/procesos").json()["filas"]
    naturalezas = {p["naturaleza"] for p in filas}
    assert "Penal 906 - Garantías" in naturalezas and "Penal 906 - Conocimiento" in naturalezas
    assert {"Tutela", "Incidente de desacato", "Hábeas corpus"} <= naturalezas
    assert {p["area"] for p in filas} >= {"Civil", "Familia", "Penal", "Constitucional"}

    # un proceso de garantías con sus solicitudes, una cerrada y otra abierta
    gar = next(p for p in filas if p["naturaleza"] == "Penal 906 - Garantías")
    d = admin.get("/api/procesos/" + gar["id"]).json()
    assert len(d["solicitudes_penales"]) == 2
    assert [bool(s["salida"]) for s in d["solicitudes_penales"]] == [True, False]
    assert d["noticia_criminal"]

    # audiencias: hay movimiento y al menos una por confirmar
    aud = admin.get("/api/audiencias").json()
    assert aud["total"] >= 4 and aud["pendientes"]
    assert aud["kpis"]["Realizada"] >= 1 and aud["kpis"]["Aplazada"] >= 1
    assert any(x["aud_causa"] for x in aud["filas"]), "alguna audiencia debe traer causa"
    assert admin.get("/api/tablero").json()["audiencias_pendientes"] == len(aud["pendientes"])

    # estadística: secciones con movimiento, los dos datos manuales y el Excel oficial
    periodo = {"desde": (date.today() - timedelta(days=500)).isoformat(), "hasta": (date.today() + timedelta(days=30)).isoformat()}
    est = admin.get("/api/estadistica", params=periodo).json()
    assert est["kpis"]["con_movimiento"] >= 6 and est["kpis"]["manuales"] == 2
    con = {x["code"] for x in est["secciones"] if x["total"]}
    assert {"SEC4587", "SEC5959", "SEC4603", "SEC5414", "SEC4416", "SEC5082"} <= con
    assert admin.get("/api/estadistica/oficial.xlsx", params=periodo).status_code == 200
