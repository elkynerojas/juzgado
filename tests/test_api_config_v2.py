"""Catálogos y personal de la v2 a través de la API (fase 9.4)."""

import pytest

from app.server.domain import audiencias as Aud
from app.server.domain import naturaleza as N

NATURALEZAS = [
    "Civil",
    "Familia",
    "Tutela",
    "Incidente de desacato",
    "Hábeas corpus",
    "Otro",
    "Penal 906 - Garantías",
    "Penal 906 - Conocimiento",
    "Penal 1826 - Garantías",
    "Penal 1826 - Conocimiento",
]


def test_config_trae_los_catalogos_de_la_v2(admin):
    c = admin.get("/api/config").json()
    assert c["naturalezas"] == list(N.NATURALEZAS) and "Penal" in c["naturalezas"]
    assert c["leyes_penales"] == ["906", "1826"] and c["procedimientos_penales"] == ["Garantías", "Conocimiento"]
    assert c["areas"] == ["Civil", "Familia", "Penal", "Constitucional", "Otros"]
    assert c["modos_cierre"] == ["", "Providencia", "Ejecutoria", "Cumplimiento"]
    assert c["personal"] == []
    assert c["audiencias"]["estados"][0] == "Programada" and len(c["audiencias"]["estados"]) == 5
    assert set(c["audiencias"]["causas"]) == {"civil_aplazada", "civil_cancelada", "penal_aplazada", "penal_cancelada"}
    assert c["actuacion"]["ejec_dias"] == 3 and "Apelación" in c["actuacion"]["recursos"]
    assert "Remates" in c["actuacion"]["tramites_posteriores"]
    assert len(c["paletas"]) == 6 and c["paletas"][0] == ["#1f3864", "Azul institucional"]
    # las listas enormes que dependen de la naturaleza no viajan aquí
    assert "delitos" not in c and "tipo_sierju" not in c


@pytest.mark.parametrize("naturaleza", NATURALEZAS)
def test_listas_por_naturaleza_vienen_del_dominio(admin, naturaleza):
    d = admin.get("/api/config/naturaleza", params={"naturaleza": naturaleza}).json()
    assert d["tipo_sierju"] == N.lista_sierju(naturaleza)
    assert d["salidas"] == N.lista_salidas(naturaleza)
    assert d["entradas"] == N.entradas_sierju(naturaleza)
    assert d["penal_solicitudes"] == N.penal_solicitudes(naturaleza)
    assert d["salidas_act"] == N.salidas_act(naturaleza)
    assert d["aud_tipos"] == Aud.tipos(naturaleza)
    assert d["area"] == N.area_de(naturaleza)
    assert (d["es_penal"], d["es_garantias"]) == (N.es_penal(naturaleza), N.es_garantias(naturaleza))


def test_sugerencia_de_tipo_sierju_se_expone(admin):
    def sug(naturaleza, clase):
        return admin.get("/api/config/naturaleza", params={"naturaleza": naturaleza, "clase": clase}).json()["sugerido"]

    assert sug("Civil", "Ejecutivo hipotecario") == "Ejecutivos-Hipotecario"
    assert sug("Familia", "Alimentos") == "Alimentos (fijación/aumento/disminución/exoneración)"
    assert sug("Hábeas corpus", "") == "Acción de hábeas corpus"
    # la v2 clasificaba el desacato como civil porque comparaba con "Desacato"
    assert sug("Incidente de desacato", "Derecho de petición") == "Derecho de petición"


def test_delitos_unificados(admin):
    d = admin.get("/api/config/delitos", params={"procedimiento": "Garantías"}).json()
    assert d and {x["ley"] for x in d} == {"906", "1826"}
    assert [x["delito"] for x in d] == [x for x, _ in N.delitos_unificados("Garantías")]
    assert admin.get("/api/config/delitos", params={"procedimiento": "Conocimiento"}).json() != d


def test_personal_crud_y_permisos(admin, crear_usuario):
    r = admin.post("/api/config/personal", json={"nombre": "Ana Ruiz", "cargo": "Escribiente"})
    assert r.status_code == 201, r.text
    x = r.json()
    assert (x["nombre"], x["cargo"], x["activo"]) == ("Ana Ruiz", "Escribiente", True)
    assert admin.get("/api/config").json()["personal"] == [x]

    y = admin.put(f"/api/config/personal/{x['id']}", json={"nombre": "Ana Ruiz", "cargo": "Citador", "activo": False}).json()
    assert (y["cargo"], y["activo"]) == ("Citador", False)
    assert admin.get("/api/config/personal").json() == [y]

    # los cargos los sembró la migración 0002
    assert "Citador" in [c["valor"] for c in admin.get("/api/config").json()["catalogos"]["cargos"]]

    consulta = crear_usuario("lector", "Consulta")
    assert consulta.get("/api/config/personal").status_code == 200
    assert consulta.post("/api/config/personal", json={"nombre": "X"}).status_code == 403
    assert consulta.delete(f"/api/config/personal/{x['id']}").status_code == 403

    assert admin.delete(f"/api/config/personal/{x['id']}").status_code == 204
    assert admin.get("/api/config/personal").json() == []
    assert admin.delete(f"/api/config/personal/{x['id']}").status_code == 404
