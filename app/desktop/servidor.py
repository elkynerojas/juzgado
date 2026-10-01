import threading
import time

import uvicorn

from app.desktop import red
from app.server.app import create_app


def iniciar(host: str, puerto: int) -> uvicorn.Server:
    # log_config=None: los registros van al logging ya configurado (archivo), no a una consola que el .exe no tiene
    server = uvicorn.Server(uvicorn.Config(create_app(tareas=True), host=host, port=puerto, log_config=None))
    threading.Thread(target=server.run, daemon=True, name="servidor").start()
    return server


def esperar(url: str, timeout: float = 20.0) -> None:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if red.responde(url, timeout=1):
            return
        time.sleep(0.15)
    raise RuntimeError(f"El servidor no respondió en {url}")
