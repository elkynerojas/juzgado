import argparse
import threading
import time
import urllib.request

import uvicorn

from app.server.app import create_app

PUERTO = 8765


def iniciar_servidor(host: str, port: int) -> uvicorn.Server:
    server = uvicorn.Server(uvicorn.Config(create_app(tareas=True), host=host, port=port, log_level="info"))
    threading.Thread(target=server.run, daemon=True).start()
    return server


def esperar_servidor(url: str, timeout: float = 15.0) -> None:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=1):
                return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError(f"El servidor no respondió en {url}")


def main() -> None:
    p = argparse.ArgumentParser(prog="control-procesos")
    p.add_argument("--host", default="0.0.0.0", help="interfaz donde escucha el servidor")
    p.add_argument("--port", type=int, default=PUERTO)
    p.add_argument("--cliente", metavar="URL", help="modo cliente: abre la ventana contra un servidor remoto")
    p.add_argument("--sin-ventana", action="store_true", help="solo servidor, sin ventana nativa")
    args = p.parse_args()

    if args.cliente:
        url = args.cliente.rstrip("/")
    else:
        url = f"http://127.0.0.1:{args.port}"
        if args.sin_ventana:
            uvicorn.run(create_app(tareas=True), host=args.host, port=args.port)
            return
        iniciar_servidor(args.host, args.port)
    esperar_servidor(url)

    from app.desktop.window import abrir_ventana

    abrir_ventana(url)


if __name__ == "__main__":
    main()
