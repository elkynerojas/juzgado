from datetime import date, timedelta

from app.server.db.seeds import cargar_catalogos


def dia(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


PROC = {"radicado": " 2026-00123 ", "naturaleza": "Civil", "clase": "Ejecutivo", "demandante": "Banco", "demandado": "Pérez", "fecha_rad": ""}


def test_ciclo_de_un_proceso(admin):
    r = admin.post("/api/procesos", json=PROC)
    assert r.status_code == 201
    p = r.json()
    assert p["radicado"] == "2026-00123" and p["fecha_rad"] is None and p["version"] == 1 and p["situacion"] == "Activo"
    assert admin.post("/api/procesos", json={"radicado": "  "}).status_code == 422

    r = admin.put(f"/api/procesos/{p['id']}", json=PROC | {"situacion": "Suspendido", "fecha_rad": "2026-03-01", "version": 1})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["fecha_rad"] == "2026-03-01"
    # edición con versión vieja: otro usuario ya lo cambió
    assert admin.put(f"/api/procesos/{p['id']}", json=PROC | {"version": 1}).status_code == 409
    r = admin.put(f"/api/procesos/{p['id']}/notas", json={"notas": "posible sentencia anticipada", "version": 2})
    assert r.json()["notas"] == "posible sentencia anticipada" and r.json()["situacion"] == "Suspendido"

    d = admin.get(f"/api/procesos/{p['id']}").json()
    assert d["derivado"]["inactividad"] == "— (suspendido)" and d["actuaciones"] == []
    assert admin.get("/api/procesos/noexiste").status_code == 404
    assert admin.delete(f"/api/procesos/{p['id']}").status_code == 204
    assert admin.get("/api/procesos").json() == []


def test_actuaciones_y_derivados(admin):
    pid = admin.post("/api/procesos", json=PROC).json()["id"]
    base = f"/api/procesos/{pid}/actuaciones"
    assert admin.post(base, json={"descripcion": ""}).status_code == 422
    assert admin.post("/api/procesos/noexiste/actuaciones", json={"descripcion": "x"}).status_code == 404

    a = admin.post(base, json={"descripcion": "Memorial recibido", "fecha_memorial": dia(-4), "constancia": "", "termino_dias": ""}).json()
    assert a["derivado"]["codigo"] == 3 and a["derivado"]["situacion"] == "Secretaría: sin constancia"
    assert a["derivado"]["dias"] == 4 and a["derivado"]["ubicacion"] == "Secretaría"

    datos = {k: a[k] for k in a if k not in ("derivado", "siguiente", "id", "proceso_id")}
    a = admin.put(f"/api/actuaciones/{a['id']}", json=datos | {"constancia": dia(-3), "pasa": "Sí", "pase": dia(-2)}).json()
    assert a["derivado"]["codigo"] == 5 and a["derivado"]["ubicacion"] == "Despacho" and a["version"] == 2
    assert admin.put(f"/api/actuaciones/{a['id']}", json=datos | {"version": 1}).status_code == 409

    d = admin.get(f"/api/procesos/{pid}").json()
    assert d["derivado"]["rep_despacho"] == 1 and d["derivado"]["inactividad"] == "Juzgado (despacho)"
    assert d["derivado"]["dias_sin_mov"] == 2 and len(d["actuaciones"]) == 1

    lista = admin.get("/api/procesos", params={"filtro": "ad"}).json()
    assert [p["id"] for p in lista] == [pid]
    assert admin.get("/api/procesos", params={"filtro": "sc"}).json() == []
    assert len(admin.get("/api/procesos", params={"q": "MEMORIAL rec"}).json()) == 1
    assert admin.get("/api/procesos", params={"q": "zzz"}).json() == []

    assert admin.delete(f"/api/actuaciones/{a['id']}").status_code == 204
    assert admin.get(f"/api/procesos/{pid}").json()["actuaciones"] == []


def test_vista_previa_y_calendario(admin):
    previa = {"origen": "Vencimiento de término", "termino": "(personalizado)", "termino_dias": 3, "termino_habil": False, "fecha_inicio": dia(-1)}
    d = admin.post("/api/actuaciones/derivar", json=previa).json()
    assert d["codigo"] == 1 and d["vencimiento"] == dia(2) and d["est_termino"] == "Próximo a vencer"
    assert d["termino_info"] == {"dias": 3, "habil": False}
    assert admin.post("/api/actuaciones/derivar", json={}).json()["codigo"] == 2

    # término hábil de catálogo: una suspensión corre el vencimiento
    habil = {"origen": "Vencimiento de término", "termino": "Traslado Avalúos", "fecha_inicio": "2026-10-13"}
    assert admin.post("/api/actuaciones/derivar", json=habil).json()["vencimiento"] == "2026-10-16"
    assert admin.get("/api/config/calendario/verificar", params={"fecha": "2026-10-14"}).json()["habil"] is True
    s = admin.post("/api/config/calendario/suspensiones", json={"desde": "2026-10-15", "hasta": "2026-10-14", "motivo": "paro"}).json()
    assert (s["desde"], s["hasta"]) == ("2026-10-14", "2026-10-15")
    assert admin.get("/api/config/calendario/verificar", params={"fecha": "2026-10-14"}).json()["habil"] is False
    assert admin.post("/api/actuaciones/derivar", json=habil).json()["vencimiento"] == "2026-10-20"
    assert admin.delete(f"/api/config/calendario/suspensiones/{s['id']}").status_code == 204
    # festivo reabierto y día cerrado
    assert admin.get("/api/config/calendario/verificar", params={"fecha": "2026-10-12"}).json()["habil"] is False
    admin.post("/api/config/calendario/dias", json={"fecha": "2026-10-12", "tipo": "reabierto"})
    admin.post("/api/config/calendario/dias", json={"fecha": "2026-10-12", "tipo": "reabierto"})
    admin.post("/api/config/calendario/dias", json={"fecha": "2026-10-13", "tipo": "cerrado"})
    cal = admin.get("/api/config").json()["calendario"]
    assert cal["reabiertos"] == ["2026-10-12"] and cal["cerrados"] == ["2026-10-13"]
    assert admin.get("/api/config/calendario/verificar", params={"fecha": "2026-10-12"}).json()["habil"] is True
    assert admin.delete("/api/config/calendario/dias/reabierto/2026-10-12").status_code == 204
    assert admin.delete("/api/config/calendario/festivos/2026-10-12").status_code == 204
    assert admin.get("/api/config/calendario/verificar", params={"fecha": "2026-10-12"}).json()["habil"] is True


def test_ruta_propone_siguiente_paso(admin):
    pid = admin.post("/api/procesos", json=PROC).json()["id"]
    base = f"/api/procesos/{pid}/actuaciones"
    paso0 = {"descripcion": "Traslado", "cuaderno": "Liquidación de costas", "origen": "Vencimiento de término",
             "termino": "Traslado Liquidación de costas", "fecha_inicio": dia(-20), "ruta_id": "r_traslado", "paso_idx": 0}
    a = admin.post(base, json=paso0).json()
    assert a["derivado"]["est_termino"] == "Vencido"
    assert a["siguiente"]["idx"] == 1 and a["siguiente"]["paso"]["nombre"] == "Resolver (decisión del despacho)"
    admin.post(base, json=paso0 | {"descripcion": "Resolver", "paso_idx": 1})
    acts = {x["descripcion"]: x for x in admin.get(f"/api/procesos/{pid}").json()["actuaciones"]}
    assert acts["Traslado"]["siguiente"] is None
    assert acts["Resolver"]["siguiente"]["idx"] == 2


def test_ejemplos_tablero_y_paquetes(admin):
    assert admin.post("/api/datos/ejemplos").json() == {"procesos": 6, "actuaciones": 17}
    t = admin.get("/api/tablero").json()
    assert t["procesos"] == 6 and t["hoy"] == dia(0)
    assert sum(x["total"] for x in t["por_situacion"]) == 17
    por_codigo = {x["codigo"]: x["total"] for x in t["por_situacion"]}
    assert (t["sin_constancia"], t["falta_pasar"], t["al_despacho"]) == (por_codigo[3], por_codigo[4], por_codigo[5])
    assert t["al_despacho"] == 4 and t["falta_pasar"] == 2 and por_codigo[0] == 1
    fechas = [x["fecha"] for x in t["proximos"]]
    assert fechas == sorted(fechas) and all(x["faltan"] > 0 for x in t["proximos"])

    procesos = admin.get("/api/procesos").json()
    assert len(procesos) == 6
    assert {p["radicado"] for p in admin.get("/api/procesos", params={"filtro": "susp"}).json()} == {"2024-00112"}
    assert admin.get("/api/procesos", params={"q": "davivienda"}).json()[0]["radicado"] == "2021-00089"

    pq = admin.get("/api/paquetes").json()
    assert pq["total"] == 16 == len(pq["filas"]) == sum(pq["materias"].values())
    activas = [x["derivado"]["fecha_activa"] or "9999" for x in pq["filas"]]
    assert activas == sorted(activas)
    liq = admin.get("/api/paquetes", params={"materia": "Liquidación de crédito"}).json()
    assert len(liq["filas"]) == pq["materias"]["Liquidación de crédito"] == 2 and liq["total"] == 16
    assert all(x["derivado"]["codigo"] == 5 for x in admin.get("/api/paquetes", params={"situacion": 5}).json()["filas"])
    assert len(admin.get("/api/paquetes", params={"tipo": "Nulidad procesal"}).json()["filas"]) == 1
    assert admin.get("/api/paquetes", params={"q": "banco agrario"}).json()["filas"][0]["radicado"] == "2019-00327"

    r = admin.get("/api/paquetes.csv", params={"materia": "Liquidación de crédito"})
    assert r.headers["content-type"].startswith("text/csv")
    lineas = r.content.decode("utf-8").splitlines()
    assert lineas[0].startswith("﻿Radicado;Partes;Cuaderno") and len(lineas) == 3
    assert '"Banco Agrario de Colombia S.A. c/ Elcy Yaneth González Buitrago"' in r.text

    assert admin.post("/api/datos/vaciar").json() == {"procesos": 0, "actuaciones": 0}
    assert admin.get("/api/tablero").json()["procesos"] == 0


def test_configuracion(admin):
    c = admin.get("/api/config").json()
    semilla = cargar_catalogos()
    assert [x["valor"] for x in c["catalogos"]["cuadernos"]] == semilla["cuadernos"]
    assert len(c["terminos"]) == 49 and len(c["rutas"]) == 7 and len(c["plantillas"]) == 7
    assert c["juzgado"]["prefijo"] == "54-172-40-89-001-" and c["tiene_membrete"] is True
    assert c["tipo_ruta"]["Recurso de apelación"] == "r_recurso"
    assert len(c["situaciones"]) == 10 and c["sugerencias_termino"]["Nulidad"] == "Traslado escrito de nulidad"

    # catálogos
    v = admin.post("/api/config/catalogos/materias", json={"valor": "Tutela"}).json()
    assert admin.post("/api/config/catalogos/materias", json={"valor": "Tutela"}).status_code == 409
    assert admin.post("/api/config/catalogos/inventado", json={"valor": "x"}).status_code == 404
    assert admin.put(f"/api/config/catalogos/materias/{v['id']}", json={"valor": "Acción de tutela"}).json()["valor"] == "Acción de tutela"
    assert admin.put(f"/api/config/catalogos/cuadernos/{v['id']}", json={"valor": "x"}).status_code == 404
    assert admin.get("/api/config").json()["catalogos"]["materias"][-1]["valor"] == "Acción de tutela"
    assert admin.delete(f"/api/config/catalogos/materias/{v['id']}").status_code == 204

    # términos
    t = admin.post("/api/config/terminos", json={"nombre": "Traslado tutela", "dias": 2, "habil": True, "categoria": "Traslado"}).json()
    assert admin.post("/api/config/terminos", json={"nombre": "Traslado tutela", "dias": 2}).status_code == 409
    assert admin.post("/api/config/terminos", json={"nombre": "Malo", "dias": 0}).status_code == 422
    assert admin.put(f"/api/config/terminos/{t['id']}", json={"nombre": "Traslado tutela", "dias": 3}).json()["dias"] == 3
    assert admin.delete(f"/api/config/terminos/{t['id']}").status_code == 204

    # rutas, pasos y asociación
    ruta = admin.post("/api/config/rutas", json={"nombre": "Tutela", "descripcion": "Trámite"}).json()
    paso = admin.post(f"/api/config/rutas/{ruta['id']}/pasos", json={"nombre": "Admitir"}).json()
    admin.post(f"/api/config/rutas/{ruta['id']}/pasos", json={"nombre": "Fallar", "origen": "Providencia (auto/sentencia)"})
    assert admin.put(f"/api/config/pasos/{paso['id']}", json={"nombre": "Admitir tutela"}).json()["nombre"] == "Admitir tutela"
    assert admin.put("/api/config/tipo-ruta", json={"tipo_solicitud": "Memorial", "ruta_id": ruta["id"]}).status_code == 200
    assert admin.put("/api/config/tipo-ruta", json={"tipo_solicitud": "Memorial", "ruta_id": "noexiste"}).status_code == 404
    c = admin.get("/api/config").json()
    assert [p["nombre"] for p in c["rutas"][-1]["pasos"]] == ["Admitir tutela", "Fallar"]
    assert c["tipo_ruta"]["Memorial"] == ruta["id"]
    assert admin.put("/api/config/tipo-ruta", json={"tipo_solicitud": "Oficio", "ruta_id": None}).json()["ruta_id"] is None
    assert admin.delete(f"/api/config/rutas/{ruta['id']}").status_code == 204
    c = admin.get("/api/config").json()
    assert "Memorial" not in c["tipo_ruta"] and "Oficio" not in c["tipo_ruta"] and len(c["rutas"]) == 7

    # juzgado y membrete
    assert admin.put("/api/config/juzgado", json={"juzgado": "JUZGADO X", "ciudad": "CÚCUTA", "prefijo": "54-"}).status_code == 200
    assert admin.get("/api/config").json()["juzgado"] == {"juzgado": "JUZGADO X", "ciudad": "CÚCUTA", "prefijo": "54-"}
    assert admin.get("/api/config/membrete").content.startswith(b"\x89PNG")
    assert admin.put("/api/config/membrete", content=b"GIF89a...", headers={"content-type": "image/gif"}).status_code == 204
    r = admin.get("/api/config/membrete")
    assert r.content == b"GIF89a..." and r.headers["content-type"] == "image/gif"
    assert admin.put("/api/config/membrete", content=b"hola", headers={"content-type": "text/plain"}).status_code == 415
    assert admin.put("/api/config/membrete", content=b"x" * (2 * 1024 * 1024 + 1), headers={"content-type": "image/png"}).status_code == 413


def test_plantillas_firmantes_y_documentos(admin):
    c = admin.get("/api/config").json()
    f0 = c["firmantes"][0]
    assert f0["tiene_firma"] and admin.get(f"/api/config/firmantes/{f0['id']}/firma").content.startswith(b"\x89PNG")
    f = admin.post("/api/config/firmantes", json={"nombre": "ANA RUIZ", "cargo": "Escribiente"}).json()
    assert f["tiene_firma"] is False and admin.get(f"/api/config/firmantes/{f['id']}/firma").status_code == 404
    assert admin.put(f"/api/config/firmantes/{f['id']}/firma", content=b"\x89PNGx", headers={"content-type": "image/png"}).json()["tiene_firma"]
    assert admin.put(f"/api/config/firmantes/{f['id']}", json={"nombre": "ANA RUIZ P.", "cargo": "Oficial mayor"}).json()["cargo"] == "Oficial mayor"

    assert admin.post("/api/config/plantillas", json={"nombre": "x", "tipo": "Otro"}).status_code == 422
    t = admin.post("/api/config/plantillas", json={"nombre": "Mía", "tipo": "Constancia", "cuerpo": "{{radicado_full}} | {{descripcion}} | {{termino}} vence {{vencimiento}} | {{fecha_letras}} | {{ciudad}} | {{motivo_pase}}"}).json()

    pid = admin.post("/api/procesos", json=PROC).json()["id"]
    a = admin.post(f"/api/procesos/{pid}/actuaciones", json={
        "descripcion": "traslado <b>del avalúo</b>", "origen": "Vencimiento de término", "termino": "(personalizado)",
        "termino_dias": 10, "termino_habil": False, "fecha_inicio": "2026-10-05", "constancia": "2026-10-06",
    }).json()
    doc = admin.post(f"/api/actuaciones/{a['id']}/documento/texto", json={"plantilla_id": t["id"], "motivo": "Recurso"}).json()
    assert doc["fecha"] == "2026-10-06"  # la de la constancia, no la de hoy
    assert doc["cuerpo"] == (
        "54-172-40-89-001-2026-00123-00 | traslado <b>del avalúo</b> | (personalizado) vence 15 de octubre de 2026"
        " | seis (6) de octubre de dos mil veintiséis (2026) | CHINÁCOTA | Recurso"
    )
    doc2 = admin.post(f"/api/actuaciones/{a['id']}/documento/texto", json={"plantilla_id": t["id"], "fecha": "2026-11-21"}).json()
    assert doc2["fecha"] == "2026-11-21" and "veintiuno (21) de noviembre" in doc2["cuerpo"]

    r = admin.post(f"/api/actuaciones/{a['id']}/documento/html", json={"cuerpo": doc["cuerpo"] + "\nlínea 2", "fecha": doc["fecha"], "firmante_id": f0["id"]})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "CONSTANCIA SECRETARIAL" in r.text and "<b>Proceso:</b> Ejecutivo" in r.text
    assert "traslado &lt;b&gt;del avalúo&lt;/b&gt;" in r.text and "<br>línea 2" in r.text
    assert "CHINÁCOTA, 6 de octubre de 2026." in r.text and r.text.count("data:image/png;base64,") == 2
    # firmante sin imagen: sale nombre y cargo
    g = admin.post("/api/config/firmantes", json={"nombre": "LUIS <MORA>", "cargo": "Citador"}).json()
    r = admin.post(f"/api/actuaciones/{a['id']}/documento/html", json={"cuerpo": "x", "firmante_id": g["id"]})
    assert '<p class="fnom">LUIS &lt;MORA&gt;</p><p class="fcar">Citador</p>' in r.text

    assert admin.put(f"/api/config/plantillas/{t['id']}", json={"nombre": "Mía 2", "tipo": "Pase al despacho", "cuerpo": "x"}).json()["tipo"] == "Pase al despacho"
    assert admin.delete(f"/api/config/plantillas/{t['id']}").status_code == 204
    assert admin.delete(f"/api/config/firmantes/{f['id']}").status_code == 204


def test_auditoria(admin, crear_usuario):
    escribiente = crear_usuario("escribiente", "Escribiente")
    p = escribiente.post("/api/procesos", json=PROC).json()
    a = escribiente.post(f"/api/procesos/{p['id']}/actuaciones", json={"descripcion": "Memorial"}).json()
    escribiente.put(f"/api/procesos/{p['id']}", json=PROC | {"demandado": "Gómez", "version": 1})
    admin.delete(f"/api/procesos/{p['id']}")

    r = admin.get("/api/auditoria", params={"entidad": "proceso", "entidad_id": p["id"]}).json()
    assert r["total"] == 3
    eliminar, editar, crear = r["filas"]  # más reciente primero
    assert (crear["accion"], crear["usuario_nombre"], crear["antes"]) == ("crear", "escribiente", None)
    assert editar["accion"] == "editar" and editar["antes"]["demandado"] == "Pérez" and editar["despues"]["demandado"] == "Gómez"
    assert eliminar["usuario_nombre"] == "admin" and eliminar["despues"] is None
    assert [x["id"] for x in eliminar["antes"]["actuaciones"]] == [a["id"]]

    assert admin.get("/api/auditoria", params={"usuario": "escribiente"}).json()["total"] == 3
    hoy = date.today()
    assert admin.get("/api/auditoria", params={"desde": (hoy + timedelta(days=2)).isoformat()}).json()["total"] == 0
    assert admin.get("/api/auditoria", params={"desde": (hoy - timedelta(days=2)).isoformat(), "limite": 2}).json()["filas"].__len__() == 2
    usuarios = admin.get("/api/auditoria", params={"entidad": "usuario"}).json()["filas"]
    assert all("password_hash" not in str(x) for x in usuarios) and len(usuarios) == 2
