import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.server.services import programador
from tests.conftest import ADMIN, golden

PROC = {"radicado": "2026-00123", "clase": "Ejecutivo", "demandante": "Banco", "demandado": "Pérez", "fecha_rad": "2026-03-01"}


def estado(c) -> dict:
    """Todo lo que debe sobrevivir a un respaldo, sin los campos que cambian solos."""
    r = c.get("/api/respaldo").json()
    r.pop("generado")
    return r


def test_exportar_vaciar_restaurar_deja_todo_igual(admin):
    admin.post("/api/datos/ejemplos")
    pid = admin.post("/api/procesos", json=PROC).json()["id"]
    admin.post(f"/api/procesos/{pid}/actuaciones", json={"descripcion": "Memorial", "fecha_memorial": "2026-09-01", "termino": "(personalizado)", "termino_dias": 4})
    admin.post("/api/config/catalogos/materias", json={"valor": "Tutela"})
    admin.post("/api/config/calendario/suspensiones", json={"desde": "2026-11-03", "hasta": "2026-11-05", "motivo": "paro"})
    admin.post("/api/config/calendario/dias", json={"fecha": "2026-10-12", "tipo": "reabierto"})
    admin.put("/api/config/juzgado", json={"juzgado": "JUZGADO X", "ciudad": "CÚCUTA", "prefijo": "54-"})

    r = admin.get("/api/respaldo")
    assert "attachment" in r.headers["content-disposition"] and r.headers["content-type"] == "application/json"
    respaldo = r.json()
    assert respaldo["formato"] == "control-procesos" and len(respaldo["procesos"]) == 7 and len(respaldo["actuaciones"]) == 18
    assert respaldo["procesos"][-1]["creado_por"] == "admin"
    assert respaldo["config"]["membrete"].startswith("data:image/png;base64,")
    antes = estado(admin)

    # se daña todo
    admin.post("/api/datos/vaciar")
    admin.put("/api/config/juzgado", json={"juzgado": "OTRO", "ciudad": "", "prefijo": ""})
    admin.put("/api/config/membrete", content=b"GIF89a", headers={"content-type": "image/gif"})
    terminos = admin.get("/api/config").json()["terminos"]
    admin.delete(f"/api/config/terminos/{terminos[0]['id']}")
    admin.delete("/api/config/rutas/r_traslado")
    assert estado(admin) != antes

    r = admin.post("/api/respaldo/restaurar", json=respaldo)
    assert r.status_code == 200, r.text
    assert r.json() | {"respaldo_previo": ""} == {
        "formato": "control-procesos", "procesos": 7, "actuaciones": 18, "actuaciones_omitidas": 0,
        "usuarios_restaurados": 0, "respaldo_previo": "",
    }  # fmt: skip
    assert estado(admin) == antes
    assert admin.get(f"/api/procesos/{pid}").json()["actuaciones"][0]["derivado"]["codigo"] == 3
    # quedó el respaldo previo del estado dañado y la sesión sigue viva
    archivos = admin.get("/api/respaldo/archivos").json()
    assert [a["nombre"] for a in archivos] == [r.json()["respaldo_previo"]] and not archivos[0]["automatico"]
    previo = admin.get(f"/api/respaldo/archivos/{archivos[0]['nombre']}").json()
    assert previo["procesos"] == [] and previo["config"]["juzgado"]["juzgado"] == "OTRO"
    assert admin.get("/api/auditoria", params={"entidad": "datos", "entidad_id": "restaurar"}).json()["total"] == 1


def test_restaurar_respaldo_del_html_original(admin):
    legacy = golden("respaldo_legacy.json")
    assert "formato" not in legacy and len(legacy["actuaciones"]) == 18
    usuarios_antes = admin.get("/api/usuarios").json()
    r = admin.post("/api/respaldo/restaurar", json=legacy)
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["formato"], res["procesos"], res["actuaciones"], res["actuaciones_omitidas"]) == ("legacy", 6, 17, 1)

    procesos = admin.get("/api/procesos").json()
    assert {p["id"] for p in procesos} == {p["id"] for p in legacy["procesos"]}  # se conservan los ids
    p0 = admin.get(f"/api/procesos/{legacy['procesos'][0]['id']}").json()
    assert p0["notas"] == "Nota del respaldo viejo" and p0["fecha_rad"] == "2019-05-10" and len(p0["actuaciones"]) == 4
    a0 = next(a for a in p0["actuaciones"] if a["id"] == legacy["actuaciones"][0]["id"])
    assert a0["tipo_solicitud"] == "Liquidación del crédito" and a0["pase"] == legacy["actuaciones"][0]["pase"] and a0["pasa"] == "Sí"

    c = admin.get("/api/config").json()
    assert c["juzgado"] == {"juzgado": "JUZGADO DE PRUEBA", "ciudad": "CHINÁCOTA NORTE DE SANTANDER", "prefijo": "99-000-"}
    assert c["catalogos"]["materias"][-1]["valor"] == "Materia propia" and len(c["catalogos"]["asuntos_familia"]) == 33
    terminos = {t["nombre"]: t for t in c["terminos"]}
    assert len(terminos) == 50 and terminos["Traslado de la demanda"]["dias"] == 25
    assert terminos["Término propio"] == terminos["Término propio"] | {"dias": 7, "habil": False, "responsable": "Parte"}
    assert [p["nombre"] for p in c["rutas"][0]["pasos"]][-1] == "Paso extra" and c["tipo_ruta"]["Memorial"] == "r_despacho"
    cal = c["calendario"]
    assert cal["cerrados"] == ["2026-10-01"] and cal["reabiertos"] == ["2026-10-12"] and cal["suspensiones"][0]["motivo"] == "paro"
    assert len(cal["festivos"]) == 91  # el HTML no exporta festivos: se conservan los del sistema
    assert [(f["nombre"], f["tiene_firma"]) for f in c["firmantes"]] == [("JOSE LUIS MORENO MILLAN", True), ("ANA RUIZ", False)]
    assert len(c["plantillas"]) == 8 and c["tiene_membrete"]
    assert admin.get("/api/config/membrete").content.startswith(b"\x89PNG")
    assert admin.get("/api/usuarios").json() == usuarios_antes  # no toca usuarios


def test_respaldo_invalido_no_cambia_nada(admin):
    admin.post("/api/datos/ejemplos")
    antes = estado(admin)
    bueno = admin.get("/api/respaldo").json()
    malos = [
        {"hola": 1},
        {"procesos": "x", "actuaciones": []},
        {"formato": "otro", "procesos": [], "actuaciones": []},
        bueno | {"version": 99},
        bueno | {"procesos": [bueno["procesos"][0], bueno["procesos"][0]]},
        bueno | {"procesos": [bueno["procesos"][0] | {"fecha_rad": "no-es-fecha"}]},
        bueno | {"config": bueno["config"] | {"membrete": "no es una imagen"}},
        {"procesos": [{"radicado": "sin id"}], "actuaciones": []},
    ]
    for malo in malos:
        r = admin.post("/api/respaldo/restaurar", json=malo)
        assert r.status_code == 400, r.text
        assert estado(admin) == antes
    assert admin.post("/api/respaldo/restaurar", content=b"esto no es json", headers={"content-type": "application/json"}).status_code == 422


def test_restaurar_usuarios_y_roles(app, admin, crear_usuario):
    crear_usuario("juez", "Juez")
    admin.post("/api/roles", json={"nombre": "Auditor", "permisos": ["auditoria.ver"]})
    pid = admin.post("/api/procesos", json=PROC).json()["id"]
    respaldo = admin.get("/api/respaldo").json()
    assert [u["usuario"] for u in respaldo["usuarios"]] == ["admin", "juez"] and all("argon2" in u["password_hash"] for u in respaldo["usuarios"])

    # después del respaldo cambian usuarios y roles
    crear_usuario("intruso", "Consulta")
    juez = next(u for u in admin.get("/api/usuarios").json() if u["usuario"] == "juez")
    admin.put(f"/api/usuarios/{juez['id']}", json={"nombre": "Juez", "rol_id": juez["rol_id"], "activo": False})

    # sin la opción, los usuarios no se tocan
    assert admin.post("/api/respaldo/restaurar", json=respaldo).json()["usuarios_restaurados"] == 0
    assert len(admin.get("/api/usuarios").json()) == 3

    assert admin.post("/api/respaldo/restaurar", params={"usuarios": True}, json=respaldo).json()["usuarios_restaurados"] == 2
    assert admin.get("/api/me").status_code == 401  # se cierran todas las sesiones
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"usuario": "admin", "password": ADMIN["password"]}).status_code == 200
    assert {u["usuario"]: u["activo"] for u in c.get("/api/usuarios").json()} == {"admin": True, "juez": True}
    assert "Auditor" in {r["nombre"] for r in c.get("/api/roles").json()}
    assert TestClient(app).post("/api/auth/login", json={"usuario": "juez", "password": "clave-segura-2"}).status_code == 200
    assert c.get(f"/api/procesos/{pid}").status_code == 200

    # un respaldo sin administrador activo no puede dejar el sistema sin acceso
    sin_admin = respaldo | {"usuarios": [u | {"activo": False} for u in respaldo["usuarios"]]}
    assert c.post("/api/respaldo/restaurar", params={"usuarios": True}, json=sin_admin).status_code == 400
    assert c.get("/api/me").status_code == 200


def test_permisos_de_respaldo(admin, crear_usuario):
    secretario = crear_usuario("secretario", "Secretario")  # exporta pero no restaura
    respaldo = secretario.get("/api/respaldo")
    assert respaldo.status_code == 200
    assert secretario.post("/api/respaldo/restaurar", json=respaldo.json()).status_code == 403
    assert secretario.put("/api/respaldo/programacion", json={"activo": False, "hora": "07:00", "conservar": 5}).status_code == 403
    consulta = crear_usuario("lectora", "Consulta")
    assert consulta.get("/api/respaldo").status_code == 403
    assert consulta.get("/api/respaldo/archivos").status_code == 403
    # restaurar usuarios exige además poder gestionarlos
    rid = admin.post("/api/roles", json={"nombre": "Restaurador", "permisos": ["respaldo.exportar", "respaldo.restaurar"]}).json()["id"]
    assert rid
    restaurador = crear_usuario("restaurador", "Restaurador")
    assert restaurador.post("/api/respaldo/restaurar", params={"usuarios": True}, json=respaldo.json()).status_code == 403
    assert restaurador.post("/api/respaldo/restaurar", json=respaldo.json()).status_code == 200


def test_respaldo_automatico_y_archivos(app, admin):
    admin.post("/api/datos/ejemplos")
    assert admin.get("/api/respaldo/programacion").json() == {"activo": True, "hora": "18:00", "conservar": 30, "ultimo": None}
    assert admin.put("/api/respaldo/programacion", json={"activo": True, "hora": "25:00", "conservar": 3}).status_code == 422
    assert admin.put("/api/respaldo/programacion", json={"activo": True, "hora": "07:30", "conservar": 2}).json()["hora"] == "07:30"

    carpeta, sesiones = app.state.dir_respaldos, app.state.sesiones
    tarea = lambda *a: programador.tarea_diaria(sesiones, carpeta, datetime(*a))  # noqa: E731
    assert tarea(2026, 10, 1, 7, 29) is None  # aún no es la hora
    primero = tarea(2026, 10, 1, 7, 30)
    assert primero.name == "respaldo_auto_2026-10-01_073000.json"
    assert len(json.loads(primero.read_text(encoding="utf-8"))["procesos"]) == 6
    assert tarea(2026, 10, 1, 9, 0) is None  # uno por día
    assert admin.get("/api/respaldo/programacion").json()["ultimo"] == "2026-10-01"
    assert tarea(2026, 10, 2, 8, 0).name == "respaldo_auto_2026-10-02_080000.json"
    tarea(2026, 10, 3, 8, 0)
    # rotación: solo quedan los 2 más recientes
    assert sorted(p.name for p in carpeta.glob("*.json")) == ["respaldo_auto_2026-10-02_080000.json", "respaldo_auto_2026-10-03_080000.json"]
    # (se sube el límite: los archivos de arriba tienen fechas futuras y la rotación borraría el de hoy)
    admin.put("/api/respaldo/programacion", json={"activo": False, "hora": "07:30", "conservar": 5})
    assert tarea(2026, 10, 4, 8, 0) is None

    # respaldo manual en el servidor, descarga y restauración desde archivo
    nombre = admin.post("/api/respaldo/archivos").json()["nombre"]
    assert nombre.startswith("respaldo_auto_") and len(admin.get("/api/respaldo/archivos").json()) == 3
    admin.post("/api/datos/vaciar")
    assert admin.post(f"/api/respaldo/archivos/{nombre}/restaurar").json()["procesos"] == 6
    assert admin.get("/api/tablero").json()["procesos"] == 6
    for malo in ("noexiste.json", "..%2F..%2Fapi.db", "api.db"):
        assert admin.get(f"/api/respaldo/archivos/{malo}").status_code == 404
