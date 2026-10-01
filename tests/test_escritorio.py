import socket

import pytest

from app.desktop import config_local, red
from app.desktop.window import JsApi


class VentanaFalsa:
    def __init__(self):
        self.mostrada = False

    def show(self):
        self.mostrada = True


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv(config_local.ENV_CONFIG, str(tmp_path / "local"))
    monkeypatch.setenv("CONTROL_PROCESOS_DATOS", str(tmp_path / "datos"))
    return tmp_path


def puerto_disponible() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_config_local(entorno):
    assert config_local.leer() is None
    config_local.guardar({"modo": "servidor", "puerto": 9000})
    assert config_local.leer() == {"modo": "servidor", "puerto": 9000}
    config_local.guardar({"modo": "cliente", "url": "http://10.0.0.5:8765", "basura": 1})
    assert config_local.leer() == {"modo": "cliente", "url": "http://10.0.0.5:8765"}
    for malo in ({"modo": "otro"}, {"modo": "servidor", "puerto": "x"}, {"modo": "cliente", "url": ""}):
        config_local.guardar(malo)
        assert config_local.leer() is None
    (entorno / "local" / "config.json").write_text("{no es json")
    assert config_local.leer() is None
    config_local.borrar()
    config_local.borrar()


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("192.168.1.10", "http://192.168.1.10:8765"),
        (" servidor:9000/ ", "http://servidor:9000"),
        ("http://10.0.0.5:8765/", "http://10.0.0.5:8765"),
        ("https://juzgado.local", "https://juzgado.local:8765"),
    ],
)
def test_normalizar_url(texto, esperado):
    assert red.normalizar_url(texto) == esperado


@pytest.mark.parametrize("malo", ["", "   ", "ftp://x", "http://", "host:abc"])
def test_normalizar_url_invalida(malo):
    with pytest.raises(ValueError):
        red.normalizar_url(malo)


def test_red():
    libre = puerto_disponible()
    assert red.puerto_libre(libre)
    with socket.socket() as s:
        s.bind(("0.0.0.0", libre))
        s.listen()
        assert not red.puerto_libre(libre)
        assert not red.responde(f"http://127.0.0.1:{libre}", timeout=0.5)  # hay algo, pero no es la app
    assert all(not ip.startswith("127.") for ip in red.direcciones_lan())


def test_asistente_servidor_y_cliente(entorno):
    """Flujo real del primer arranque: un equipo queda de servidor y otro se conecta como cliente."""
    puerto = puerto_disponible()
    ventana = VentanaFalsa()
    api = JsApi(oculta=True)
    api._window = ventana

    r = api.inicio()
    assert r["paso"] == "asistente" and r["error"] == "" and r["puerto"] == 8765 and ventana.mostrada

    assert api.elegir_servidor("abc") == {"ok": False, "mensaje": "Puerto no válido."}
    assert api.elegir_servidor(80)["ok"] is False
    with socket.socket() as s:
        s.bind(("0.0.0.0", puerto))
        assert "ocupado" in api.elegir_servidor(puerto)["mensaje"]
    assert config_local.leer() is None  # nada se guarda si no funcionó

    r = api.elegir_servidor(str(puerto))
    assert r["ok"] and r["url"] == f"http://127.0.0.1:{puerto}"
    assert all(d.endswith(f":{puerto}") for d in r["direcciones"])
    assert config_local.leer() == {"modo": "servidor", "puerto": puerto}
    assert red.responde(r["url"])
    assert (entorno / "datos" / "control_procesos.db").exists()

    # al abrir de nuevo entra directo; una segunda instancia reutiliza el servidor que ya corre
    assert api.inicio() == {"paso": "entrar", "url": r["url"]}
    assert JsApi().inicio() == {"paso": "entrar", "url": r["url"]}

    # otro equipo, como cliente
    config_local.borrar()
    cliente = JsApi()
    cliente._window = VentanaFalsa()
    assert cliente.probar(f"127.0.0.1:{puerto}") == {"ok": True, "url": r["url"], "mensaje": "Conexión correcta."}
    muerto = puerto_disponible()
    assert cliente.probar(f"127.0.0.1:{muerto}")["ok"] is False
    assert cliente.elegir_cliente(f"127.0.0.1:{muerto}")["ok"] is False and config_local.leer() is None
    assert cliente.elegir_cliente(f"127.0.0.1:{puerto}")["ok"]
    assert config_local.leer() == {"modo": "cliente", "url": r["url"]}
    assert cliente.inicio() == {"paso": "entrar", "url": r["url"]}

    # servidor caído: vuelve el asistente con el error y la dirección ya escrita
    config_local.guardar({"modo": "cliente", "url": f"http://127.0.0.1:{muerto}"})
    r2 = cliente.inicio()
    assert r2["paso"] == "asistente" and "No se pudo conectar" in r2["error"] and r2["url"].endswith(str(muerto))

    # --cliente URL no toca la configuración guardada
    assert JsApi({"modo": "cliente", "url": r["url"]}).inicio() == {"paso": "entrar", "url": r["url"]}
    assert cliente.reconfigurar() and config_local.leer() is None
    assert cliente.abrir_en_navegador("file:///etc/passwd") is False
