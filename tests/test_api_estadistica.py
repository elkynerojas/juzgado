"""La API de estadística SIERJU: resumen, detalle, datos manuales y las tres descargas (fase 11)."""

import io
import zipfile
from datetime import date, timedelta

from app.server.domain.sierju.secciones import ACTIVAS

# los ejemplos traen fechas relativas a hoy, así que el periodo se calcula igual
DESDE = (date.today() - timedelta(days=500)).isoformat()
HASTA = (date.today() + timedelta(days=30)).isoformat()
PERIODO = {"desde": DESDE, "hasta": HASTA}


def _con_datos(admin):
    assert admin.post("/api/datos/ejemplos").status_code == 200
    return admin


def test_resumen_del_periodo(admin):
    _con_datos(admin)
    r = admin.get("/api/estadistica", params=PERIODO)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["periodo"] == PERIODO
    assert d["kpis"]["secciones"] == len(ACTIVAS) == 23
    assert d["kpis"]["con_movimiento"] > 0, "los ejemplos deben mover la estadística"
    # los ejemplos traen dos datos especiales registrados a mano
    assert d["kpis"]["automaticos"] > 0 and d["kpis"]["manuales"] == 2
    assert len(d["secciones"]) == 23 and all("title" in x for x in d["secciones"])
    # el resumen no arrastra las etiquetas: son cientos de filas por sección
    assert all("filas" not in x and "columnas" not in x for x in d["secciones"])


def test_periodo_invalido(admin):
    assert admin.get("/api/estadistica").status_code == 422
    assert admin.get("/api/estadistica", params={"desde": DESDE}).status_code == 422
    assert admin.get("/api/estadistica", params={"desde": HASTA, "hasta": DESDE}).status_code == 422


def test_detalle_de_una_seccion(admin):
    _con_datos(admin)
    conmov = next(x for x in admin.get("/api/estadistica", params=PERIODO).json()["secciones"] if x["total"])
    d = admin.get(f"/api/estadistica/secciones/{conmov['code']}", params=PERIODO).json()
    assert d["code"] == conmov["code"] and d["total"] == conmov["total"]
    assert d["detalle"] and all(x["cantidad"] > 0 for x in d["detalle"])
    # las etiquetas llegan sin el prefijo (FIL1234) del formato
    assert all(not x["fila"].startswith("(FIL") for x in d["detalle"])
    assert admin.get("/api/estadistica/secciones/SEC9999", params=PERIODO).status_code == 404
    # una sección que existe pero no está en la plantilla
    assert admin.get("/api/estadistica/secciones/SEC5957", params=PERIODO).status_code == 404


def test_etiquetas_para_el_dato_manual(admin):
    lista = admin.get("/api/estadistica/secciones").json()
    assert len(lista) == 23
    d = admin.get("/api/estadistica/secciones/SEC4603/etiquetas").json()
    assert d["filas"] and d["columnas"]
    assert all(x["valor"].startswith("(FIL") for x in d["filas"])
    assert all(not x["etiqueta"].startswith("(") for x in d["columnas"])
    assert admin.get("/api/estadistica/secciones/SEC9999/etiquetas").status_code == 404


def test_dato_manual(admin):
    e = admin.get("/api/estadistica/secciones/SEC4603/etiquetas").json()
    cuerpo = {
        "fecha": date.today().isoformat(),
        "seccion": "SEC4603",
        "fila": e["filas"][0]["valor"],
        "columna": e["columnas"][0]["valor"],
        "cantidad": 4,
        "nota": "turnos de garantías",
    }
    r = admin.post("/api/estadistica/eventos", json=cuerpo)
    assert r.status_code == 201, r.text
    creado = r.json()
    assert creado["cantidad"] == 4 and creado["nota"] == "turnos de garantías"

    d = admin.get("/api/estadistica", params=PERIODO).json()
    assert d["kpis"]["manuales"] == 1 and len(d["manuales"]) == 1  # sin ejemplos cargados
    detalle = admin.get("/api/estadistica/secciones/SEC4603", params=PERIODO).json()
    assert any(x["cantidad"] == 4 for x in detalle["detalle"])

    # fuera del periodo no cuenta
    lejos = {"desde": (date.today() + timedelta(days=400)).isoformat(), "hasta": (date.today() + timedelta(days=500)).isoformat()}
    assert admin.get("/api/estadistica", params=lejos).json()["kpis"]["manuales"] == 0

    assert admin.delete(f"/api/estadistica/eventos/{creado['id']}").status_code == 204
    assert admin.get("/api/estadistica", params=PERIODO).json()["kpis"]["manuales"] == 0
    assert admin.delete(f"/api/estadistica/eventos/{creado['id']}").status_code == 404


def test_dato_manual_debe_apuntar_a_una_celda_real(admin):
    e = admin.get("/api/estadistica/secciones/SEC4603/etiquetas").json()
    base = {"fecha": date.today().isoformat(), "seccion": "SEC4603", "fila": e["filas"][0]["valor"], "columna": e["columnas"][0]["valor"]}
    assert admin.post("/api/estadistica/eventos", json=base | {"seccion": "SEC9999"}).status_code == 422
    assert admin.post("/api/estadistica/eventos", json=base | {"seccion": "SEC5957"}).status_code == 422
    assert admin.post("/api/estadistica/eventos", json=base | {"fila": "fila inventada"}).status_code == 422
    assert admin.post("/api/estadistica/eventos", json=base | {"columna": "columna inventada"}).status_code == 422
    assert admin.post("/api/estadistica/eventos", json=base | {"proceso_id": "noexiste"}).status_code == 404
    assert admin.post("/api/estadistica/eventos", json=base | {"cantidad": 0}).status_code == 422


def test_excel_oficial(admin):
    _con_datos(admin)
    r = admin.get("/api/estadistica/oficial.xlsx", params=PERIODO)
    assert r.status_code == 200
    assert r.headers["content-disposition"] == f'attachment; filename="SIERJU_{DESDE}_a_{HASTA}.xlsx"'
    # con COL6828 en el mapa no debe quedar ninguna columna sin destino
    assert "x-columnas-sin-mapa" not in r.headers
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert z.testzip() is None
        assert "xl/styles.xml" in z.namelist() and len([n for n in z.namelist() if "worksheets/" in n]) == 24


def test_excel_generico(admin):
    _con_datos(admin)
    r = admin.get("/api/estadistica/completo.xlsx", params=PERIODO)
    assert r.status_code == 200
    assert f"SIERJU_COMPLETO_{DESDE}_{HASTA}.xlsx" in r.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if "worksheets/" in n]) == 23


def test_bitacora(admin):
    _con_datos(admin)
    r = admin.get("/api/estadistica/bitacora.csv", params=PERIODO)
    assert r.status_code == 200 and r.text.startswith("﻿")
    lineas = r.text.strip().splitlines()
    assert lineas[0].lstrip("﻿").startswith("Fecha;")
    assert len(lineas) > 1, "la bitácora debe listar los datos contados"
    assert f"SIERJU_bitacora_{DESDE}_{HASTA}.csv" in r.headers["content-disposition"]


def test_permisos(admin, crear_usuario):
    consulta = crear_usuario("lector", "Consulta")
    assert consulta.get("/api/estadistica", params=PERIODO).status_code == 200
    assert consulta.get("/api/estadistica/secciones").status_code == 403
    assert consulta.post("/api/estadistica/eventos", json={"fecha": "2026-01-01", "seccion": "x", "fila": "y", "columna": "z"}).status_code == 403
    assert consulta.get("/api/estadistica/oficial.xlsx", params=PERIODO).status_code == 403

    # el juez exporta pero no registra, como lo reparte el rol semilla
    juez = crear_usuario("juez", "Juez", "clave-segura-3")
    assert juez.get("/api/estadistica/oficial.xlsx", params=PERIODO).status_code == 200
    assert juez.get("/api/estadistica/secciones").status_code == 403
