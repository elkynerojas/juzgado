from fastapi.testclient import TestClient

from app.server.app import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_sirve_frontend():
    r = client.get("/")
    assert r.status_code == 200
    assert "Control de Procesos" in r.text


def test_documento_de_prueba():
    r = client.get("/spike/doc")
    assert r.status_code == 200
    assert "CONSTANCIA SECRETARIAL" in r.text
