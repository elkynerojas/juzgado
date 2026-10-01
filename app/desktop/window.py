import logging
import socket
import webbrowser
from pathlib import Path

import webview

from app.desktop import bandeja, config_local, red, servidor
from app.desktop.config_local import CLIENTE, PUERTO, SERVIDOR

log = logging.getLogger(__name__)
ASISTENTE = Path(__file__).resolve().parent / "asistente.html"


class JsApi:
    """Funciones de Python disponibles en la página como window.pywebview.api.*"""

    def __init__(self, forzado: dict | None = None, oculta: bool = False):
        self._window = None
        self._forzado = forzado
        self._oculta = oculta
        self._bandeja = False

    # ---------- arranque y asistente ----------

    def inicio(self) -> dict:
        """La llama la página de arranque: conecta con lo configurado o pide configurar."""
        cfg = self._forzado or config_local.leer()
        if not cfg:
            return self._asistente()
        r = self._conectar(cfg)
        if r["ok"]:
            return {"paso": "entrar", "url": r["url"]}
        return self._asistente(r["mensaje"], cfg)

    def _asistente(self, error: str = "", cfg: dict | None = None) -> dict:
        if self._oculta:
            self._window.show()
        cfg = cfg or {}
        return {
            "paso": "asistente",
            "error": error,
            "puerto": cfg.get("puerto", PUERTO),
            "url": cfg.get("url", ""),
            "equipo": socket.gethostname(),
        }

    def _conectar(self, cfg: dict) -> dict:
        try:
            if cfg["modo"] == CLIENTE:
                url = red.normalizar_url(cfg["url"])
                if not red.responde(url):
                    return {"ok": False, "mensaje": f"No se pudo conectar con el servidor en {url}. Verifique que esté encendido y con la aplicación abierta."}
                return {"ok": True, "url": url, "direcciones": []}
            puerto = int(cfg["puerto"])
            url = f"http://127.0.0.1:{puerto}"
            # si ya hay una instancia atendiendo (p. ej. en la bandeja), se usa esa
            if not red.responde(url, timeout=1):
                if not 1024 <= puerto <= 65535:
                    return {"ok": False, "mensaje": "El puerto debe estar entre 1024 y 65535."}
                if not red.puerto_libre(puerto):
                    return {"ok": False, "mensaje": f"El puerto {puerto} está ocupado por otro programa. Elija otro."}
                servidor.iniciar("0.0.0.0", puerto)
                servidor.esperar(url)
            direcciones = [f"http://{ip}:{puerto}" for ip in red.direcciones_lan()]
            if not self._bandeja:
                self._bandeja = bandeja.instalar(self._window, direcciones[0] if direcciones else url)
            return {"ok": True, "url": url, "direcciones": direcciones}
        except Exception as e:
            log.exception("No se pudo iniciar con %s", cfg)
            return {"ok": False, "mensaje": str(e) or type(e).__name__}

    def probar(self, url: str) -> dict:
        try:
            url = red.normalizar_url(url)
        except ValueError as e:
            return {"ok": False, "mensaje": str(e)}
        ok = red.responde(url)
        return {"ok": ok, "url": url, "mensaje": "Conexión correcta." if ok else f"No hay respuesta en {url}."}

    def elegir_servidor(self, puerto) -> dict:
        try:
            cfg = {"modo": SERVIDOR, "puerto": int(puerto)}
        except (TypeError, ValueError):
            return {"ok": False, "mensaje": "Puerto no válido."}
        return self._elegir(cfg)

    def elegir_cliente(self, url: str) -> dict:
        try:
            cfg = {"modo": CLIENTE, "url": red.normalizar_url(url)}
        except ValueError as e:
            return {"ok": False, "mensaje": str(e)}
        return self._elegir(cfg)

    def _elegir(self, cfg: dict) -> dict:
        r = self._conectar(cfg)
        if r["ok"]:
            config_local.guardar(cfg)
        return r

    def reconfigurar(self) -> bool:
        """Olvida el modo de este equipo; el asistente aparece al volver a abrir la aplicación."""
        config_local.borrar()
        return True

    # ---------- utilidades para la aplicación ----------

    def guardar_texto(self, nombre, contenido, descripcion="Todos los archivos (*.*)"):
        rutas = self._window.create_file_dialog(
            webview.FileDialog.SAVE, save_filename=nombre, file_types=(descripcion,)
        )
        if not rutas:
            return None
        ruta = rutas if isinstance(rutas, str) else rutas[0]
        # newline="" para no alterar los saltos de línea del CSV en Windows
        Path(ruta).write_text(contenido, encoding="utf-8", newline="")
        return ruta

    def abrir_en_navegador(self, url):
        # la página cargada puede venir de otro equipo: solo se abren direcciones web
        if not str(url).startswith(("http://", "https://")):
            return False
        webbrowser.open(url)
        return True


def abrir_ventana(forzado: dict | None = None, oculta: bool = False) -> None:
    api = JsApi(forzado, oculta)
    api._window = webview.create_window(
        "Control de Procesos",
        html=ASISTENTE.read_text(encoding="utf-8"),
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
        hidden=oculta,
    )
    webview.start()
