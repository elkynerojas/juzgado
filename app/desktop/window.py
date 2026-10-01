import webbrowser
from pathlib import Path

import webview


class JsApi:
    def __init__(self):
        self._window = None

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
        webbrowser.open(url)
        return True


def abrir_ventana(url: str) -> None:
    api = JsApi()
    api._window = webview.create_window(
        "Control de Procesos", url, js_api=api, width=1280, height=820, min_size=(900, 600)
    )
    webview.start()
