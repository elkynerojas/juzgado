def test_health(cliente):
    r = cliente.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_sirve_frontend(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "Control de Procesos" in r.text


def test_documento_de_prueba(cliente):
    r = cliente.get("/spike/doc")
    assert r.status_code == 200
    assert "CONSTANCIA SECRETARIAL" in r.text
