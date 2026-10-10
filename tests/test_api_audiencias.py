"""El panel de audiencias y sus dos operaciones: fijar y resolver (fase 10)."""

from datetime import date, timedelta

import pytest

from app.server.db.seeds import cargar_sierju
from app.server.domain import audiencias as Aud


def dia(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


CIVIL = {"radicado": "2026-00100", "naturaleza": "Civil", "clase": "Ejecutivo"}
PENAL = {
    "radicado": "2026-00200", "naturaleza": "Penal 906 - Garantías", "tipo_sierju": "ARTÍCULO 239. HURTO",
    "solicitudes_penales": [{"tipo": "Legalización de captura", "fecha": "2026-03-02"}],
}  # fmt: skip


def _proceso(admin, datos):
    r = admin.post("/api/procesos", json=datos)
    assert r.status_code == 201, r.text
    return r.json()


def _fijar(admin, pid, **kw):
    cuerpo = {"proceso_id": pid, "fecha": dia(5), "tipo": "Audiencia", "estado": "Programada"} | kw
    return admin.post("/api/audiencias", json=cuerpo)


def test_fijar_audiencia(admin):
    p = _proceso(admin, CIVIL)
    r = _fijar(admin, p["id"], fecha=dia(3), hora="09:30", asignado_a="Ana")
    assert r.status_code == 201, r.text
    a = r.json()
    assert (a["aud_fecha"], a["aud_hora"], a["aud_estado"]) == (dia(3), "09:30", "Programada")
    assert a["area"] == "Civil" and a["radicado"] == "2026-00100" and a["asignado_a"] == "Ana"
    assert a["cuaderno"] == "Principal" and a["descripcion"] == "Audiencia: Audiencia"

    # la audiencia es una actuación: aparece en el detalle del proceso
    d = admin.get("/api/procesos/" + p["id"]).json()
    act = next(x for x in d["actuaciones"] if x["es_audiencia"])
    assert act["materia"] == "Audiencia / diligencia" and act["origen"] == "Providencia (auto/sentencia)"

    assert admin.post("/api/audiencias", json={"proceso_id": "noexiste", "fecha": dia(1)}).status_code == 404


def test_pendientes_por_confirmar_y_filtros(admin):
    civil = _proceso(admin, CIVIL)
    penal = _proceso(admin, PENAL)
    _fijar(admin, civil["id"], fecha=dia(-2))          # ya pasó y sigue Programada: hay que confirmarla
    _fijar(admin, civil["id"], fecha=dia(4))           # futura
    _fijar(admin, penal["id"], fecha=dia(-1), tipo="Ley 906 Garantías")
    ya = _fijar(admin, civil["id"], fecha=dia(-3), estado="Realizada").json()

    r = admin.get("/api/audiencias").json()
    assert r["total"] == 4 and r["hoy"] == dia(0)
    assert [x["aud_fecha"] for x in r["filas"]] == sorted(x["aud_fecha"] for x in r["filas"])
    assert r["kpis"]["Programada"] == 3 and r["kpis"]["Realizada"] == 1
    # solo las que pasaron y siguen programadas
    assert {x["aud_fecha"] for x in r["pendientes"]} == {dia(-2), dia(-1)}
    assert ya["actuacion_id"] not in {x["actuacion_id"] for x in r["pendientes"]}

    assert admin.get("/api/audiencias", params={"estado": "Realizada"}).json()["total"] == 1
    assert admin.get("/api/audiencias", params={"area": "Penal"}).json()["total"] == 1
    assert admin.get("/api/audiencias", params={"desde": dia(0)}).json()["total"] == 1
    assert admin.get("/api/audiencias", params={"hasta": dia(-2)}).json()["total"] == 2
    # el contador del tablero usa las mismas pendientes
    assert admin.get("/api/tablero").json()["audiencias_pendientes"] == 2


def test_resolver_realizada(admin):
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1)).json()
    r = admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json={"version": a["version"], "estado": "Realizada"})
    assert r.status_code == 200, r.text
    assert r.json()["actuacion"]["aud_estado"] == "Realizada" and r.json()["nueva"] is None
    assert admin.get("/api/audiencias").json()["pendientes"] == []


def test_resolver_aplazada_con_causa_y_reprogramacion(admin):
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1), hora="08:00").json()
    causa = Aud.causas("Civil", "Aplazada")[0]
    # la causa tiene que ser una columna real del formato oficial
    assert causa in cargar_sierju()["audiencias"]["columnas_causa"]["civil_aplazada"]
    r = admin.post(
        f"/api/audiencias/{a['actuacion_id']}/resolver",
        json={"version": a["version"], "estado": "Aplazada", "causa": causa, "nueva_fecha": dia(10), "nueva_hora": "14:00"},
    ).json()
    assert r["actuacion"]["aud_estado"] == "Aplazada" and r["actuacion"]["aud_causa"] == causa
    nueva = r["nueva"]
    assert nueva["aud_fecha"] == dia(10) and nueva["aud_hora"] == "14:00" and nueva["aud_estado"] == "Programada"
    # hereda la clase de audiencia y deja constancia de dónde salió
    assert nueva["aud_tipo"] == a["aud_tipo"]
    assert nueva["descripcion"].startswith("Audiencia reprogramada:")

    # dos entradas de auditoría: la que se resolvió y la que nació
    aud = [x for x in admin.get("/api/auditoria").json()["filas"] if x["entidad"] == "actuacion"]
    assert [x["accion"] for x in aud] == ["crear", "editar", "crear"]


def test_una_audiencia_fijada_dentro_de_otra_no_es_reprogramacion(admin):
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1)).json()
    r = admin.post(
        f"/api/audiencias/{a['actuacion_id']}/resolver",
        json={"version": a["version"], "estado": "Realizada", "nueva_fecha": dia(20), "nuevo_tipo": "Audiencia"},
    ).json()
    assert r["nueva"]["descripcion"].startswith("Nueva audiencia fijada en diligencia:")


def test_la_causa_debe_existir_en_la_estadistica(admin):
    """La v2 guardaba etiquetas que ninguna columna SIERJU reconocía, y la causa se perdía."""
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1)).json()
    base = {"version": a["version"], "estado": "Aplazada"}
    # "Causa demás partes" era la etiqueta de la v2; la columna real dice "Causa de las demás partes"
    assert admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json=base | {"causa": "Causa demás partes"}).status_code == 422
    assert admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json=base | {"estado": "Inventada"}).status_code == 422
    # un estado que no aplaza ni cancela descarta la causa
    r = admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json=base | {"estado": "Suspendida", "causa": "lo que sea"}).json()
    assert r["actuacion"]["aud_causa"] == ""


def test_resolver_con_version_vieja_y_sobre_lo_que_no_es_audiencia(admin):
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1)).json()
    cuerpo = {"version": a["version"], "estado": "Realizada"}
    assert admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json=cuerpo).status_code == 200
    assert admin.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json=cuerpo).status_code == 409

    otra = admin.post(f"/api/procesos/{p['id']}/actuaciones", json={"descripcion": "No es audiencia"}).json()
    assert admin.post(f"/api/audiencias/{otra['id']}/resolver", json={"version": 1, "estado": "Realizada"}).status_code == 422


def test_cuadernos_del_proceso(admin):
    p = _proceso(admin, CIVIL)
    admin.post(f"/api/procesos/{p['id']}/actuaciones", json={"descripcion": "x", "cuaderno": "Medidas cautelares"})
    assert admin.get(f"/api/audiencias/cuadernos/{p['id']}").json() == ["Principal", "Medidas cautelares"]


def test_consulta_ve_pero_no_gestiona(admin, crear_usuario):
    p = _proceso(admin, CIVIL)
    a = _fijar(admin, p["id"], fecha=dia(-1)).json()
    consulta = crear_usuario("lector", "Consulta")
    assert consulta.get("/api/audiencias").status_code == 200
    assert _fijar(consulta, p["id"]).status_code == 403
    assert consulta.post(f"/api/audiencias/{a['actuacion_id']}/resolver", json={"version": 1, "estado": "Realizada"}).status_code == 403


@pytest.mark.parametrize(
    "naturaleza,esperado",
    [
        ("Civil", ["Audiencia"]),
        ("Familia", ["Audiencia"]),
        ("Penal 906 - Garantías", ["Ley 906 Garantías", "Otras audiencias"]),
        ("Penal 1826 - Conocimiento", ["Ley 1826 Audiencia concentrada", "Ley 1826 Audiencia de juicio", "Otras audiencias"]),
    ],
)
def test_clases_de_audiencia_por_naturaleza(naturaleza, esperado):
    assert Aud.tipos(naturaleza) == esperado


def test_causas_solo_cuando_el_estado_las_pide():
    assert Aud.causas("Civil", "Realizada") == []
    assert Aud.causas("Civil", "Suspendida") == []
    assert "Otras causas" in Aud.causas("Civil", "Cancelada / no realizada")
    assert Aud.causas("Penal 906 - Garantías", "Aplazada") != Aud.causas("Civil", "Aplazada")
