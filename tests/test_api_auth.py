from fastapi.testclient import TestClient

from app.server.core.permisos import PERMISOS
from tests.conftest import ADMIN


def test_instalacion_solo_una_vez(app, cliente):
    assert cliente.get("/api/estado").json() == {"inicializado": False}
    assert cliente.get("/api/me").status_code == 401
    r = cliente.post("/api/instalacion", json=ADMIN)
    assert r.status_code == 201
    assert r.json()["rol"] == "Administrador"
    assert set(r.json()["permisos"]) == set(PERMISOS)
    assert cliente.get("/api/estado").json() == {"inicializado": True}
    assert cliente.get("/api/me").json()["usuario"] == "admin"
    assert TestClient(app).post("/api/instalacion", json=ADMIN | {"usuario": "otro"}).status_code == 409


def test_instalacion_exige_clave_de_8(cliente):
    assert cliente.post("/api/instalacion", json=ADMIN | {"password": "corta"}).status_code == 422


def test_todo_exige_sesion(cliente):
    for ruta in ("/api/procesos", "/api/tablero", "/api/paquetes", "/api/config", "/api/usuarios", "/api/auditoria"):
        assert cliente.get(ruta).status_code == 401, ruta


def test_login_logout(app, admin):
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"usuario": "admin", "password": "mala"}).status_code == 401
    assert c.post("/api/auth/login", json={"usuario": "nadie", "password": ADMIN["password"]}).status_code == 401
    r = c.post("/api/auth/login", json={"usuario": "ADMIN", "password": ADMIN["password"]})
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower()
    assert c.get("/api/me").status_code == 200
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/me").status_code == 401


def test_bloqueo_por_intentos(app, admin):
    c = TestClient(app)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"usuario": "admin", "password": "mala"}).status_code == 401
    assert c.post("/api/auth/login", json={"usuario": "admin", "password": ADMIN["password"]}).status_code == 429


def test_permisos_por_rol(admin, crear_usuario):
    consulta = crear_usuario("lectora", "Consulta")
    assert set(consulta.get("/api/me").json()["permisos"]) == {"procesos.ver", "actuaciones.ver", "paquetes.ver"}
    assert consulta.get("/api/procesos").status_code == 200
    assert consulta.get("/api/paquetes").status_code == 200
    assert consulta.get("/api/config").status_code == 200
    r = consulta.post("/api/procesos", json={"radicado": "2026-00001"})
    assert r.status_code == 403
    assert "Crear procesos" in r.json()["detail"]
    for metodo, ruta in [
        ("get", "/api/paquetes.csv"), ("get", "/api/usuarios"), ("get", "/api/roles"), ("get", "/api/auditoria"),
        ("post", "/api/datos/vaciar"), ("post", "/api/datos/ejemplos"),
    ]:  # fmt: skip
        assert getattr(consulta, metodo)(ruta).status_code == 403, ruta
    assert consulta.post("/api/config/terminos", json={"nombre": "x", "dias": 3}).status_code == 403

    escribiente = crear_usuario("escribiente", "Escribiente")
    pid = escribiente.post("/api/procesos", json={"radicado": "2026-00001"}).json()["id"]
    assert escribiente.delete(f"/api/procesos/{pid}").status_code == 403
    assert admin.delete(f"/api/procesos/{pid}").status_code == 204


def test_rol_personalizado_y_cambio_de_permisos(admin, crear_usuario):
    r = admin.post("/api/roles", json={"nombre": "Auditor", "permisos": ["auditoria.ver"]})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert admin.post("/api/roles", json={"nombre": "auditor"}).status_code == 409
    assert admin.post("/api/roles", json={"nombre": "X", "permisos": ["no.existe"]}).status_code == 422
    auditor = crear_usuario("auditor", "Auditor")
    assert auditor.get("/api/auditoria").status_code == 200
    assert auditor.get("/api/procesos").status_code == 403
    # el cambio de permisos aplica de inmediato, sin volver a entrar
    r = admin.put(f"/api/roles/{rid}", json={"nombre": "Auditor", "permisos": ["procesos.ver"]})
    assert r.json()["permisos"] == ["procesos.ver"]
    assert auditor.get("/api/auditoria").status_code == 403
    assert auditor.get("/api/procesos").status_code == 200
    assert admin.delete(f"/api/roles/{rid}").status_code == 409  # tiene usuarios


def test_rol_administrador_protegido(admin):
    roles = {x["nombre"]: x for x in admin.get("/api/roles").json()}
    assert set(roles) == {"Administrador", "Juez", "Secretario", "Escribiente", "Consulta"}
    adm = roles["Administrador"]
    assert adm["es_sistema"] and set(adm["permisos"]) == set(PERMISOS) and adm["usuarios"] == 1
    assert admin.put(f"/api/roles/{adm['id']}", json={"nombre": "Admin", "permisos": []}).status_code == 400
    assert admin.delete(f"/api/roles/{adm['id']}").status_code == 400
    assert admin.delete(f"/api/roles/{roles['Juez']['id']}").status_code == 204


def test_gestion_de_usuarios(app, admin, crear_usuario):
    juez = crear_usuario("juez", "Juez")
    usuarios = {u["usuario"]: u for u in admin.get("/api/usuarios").json()}
    assert "password_hash" not in usuarios["juez"]
    yo, j = usuarios["admin"], usuarios["juez"]
    roles = {x["nombre"]: x["id"] for x in admin.get("/api/roles").json()}
    assert admin.post("/api/usuarios", json={"usuario": "JUEZ", "nombre": "x", "password": "12345678", "rol_id": roles["Juez"]}).status_code == 409

    # no se puede quedar el sistema sin administrador
    base = {"nombre": yo["nombre"], "rol_id": yo["rol_id"], "activo": True}
    assert admin.put(f"/api/usuarios/{yo['id']}", json=base | {"activo": False}).status_code == 409
    assert admin.put(f"/api/usuarios/{yo['id']}", json=base | {"rol_id": roles["Consulta"]}).status_code == 409

    # desactivar cierra la sesión y bloquea el ingreso
    assert juez.get("/api/me").status_code == 200
    assert admin.put(f"/api/usuarios/{j['id']}", json={"nombre": "Juez", "rol_id": j["rol_id"], "activo": False}).status_code == 200
    assert juez.get("/api/me").status_code == 401
    assert TestClient(app).post("/api/auth/login", json={"usuario": "juez", "password": "clave-segura-2"}).status_code == 401

    # reactivar con clave nueva
    assert admin.put(f"/api/usuarios/{j['id']}", json={"nombre": "Juez", "rol_id": j["rol_id"], "activo": True, "password": "otra-clave-9"}).status_code == 200
    assert TestClient(app).post("/api/auth/login", json={"usuario": "juez", "password": "otra-clave-9"}).status_code == 200


def test_cambiar_mi_password_y_preferencias(app, admin):
    otra = TestClient(app)
    otra.post("/api/auth/login", json={"usuario": "admin", "password": ADMIN["password"]})
    assert admin.put("/api/me/password", json={"actual": "mala", "nueva": "nueva-clave-1"}).status_code == 400
    assert admin.put("/api/me/password", json={"actual": ADMIN["password"], "nueva": "nueva-clave-1"}).status_code == 204
    assert admin.get("/api/me").status_code == 200  # la sesión actual sigue
    assert otra.get("/api/me").status_code == 401  # las demás se cierran
    assert admin.put("/api/me/preferencias", json={"modo": "dark", "basura": 1}).json() == {"color": "", "modo": "dark", "font": ""}
    assert admin.get("/api/me").json()["preferencias"]["modo"] == "dark"
