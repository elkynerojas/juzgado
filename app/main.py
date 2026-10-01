import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.desktop import config_local
from app.desktop.config_local import CLIENTE, PUERTO


def configurar_logs() -> None:
    # el .exe no tiene consola: sin esto, cualquier print o registro a stdout lo tumbaría
    for nombre in ("stdout", "stderr"):
        if getattr(sys, nombre) is None:
            setattr(sys, nombre, open(os.devnull, "w"))  # noqa: SIM115
    carpeta = config_local.dir_local() / "logs"
    carpeta.mkdir(exist_ok=True)
    archivo = RotatingFileHandler(carpeta / "control_procesos.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[archivo, logging.StreamHandler()],
    )


def main() -> None:
    p = argparse.ArgumentParser(prog="control-procesos")
    p.add_argument("--cliente", metavar="URL", help="abre la ventana contra ese servidor, sin cambiar la configuración")
    p.add_argument("--sin-ventana", action="store_true", help="solo servidor, sin ventana nativa")
    p.add_argument("--host", default="0.0.0.0", help="interfaz donde escucha el servidor (con --sin-ventana)")
    p.add_argument("--port", type=int, default=PUERTO, help="puerto del servidor (con --sin-ventana)")
    p.add_argument("--reconfigurar", action="store_true", help="vuelve a mostrar el asistente Servidor/Cliente")
    p.add_argument("--bandeja", action="store_true", help="inicia sin mostrar la ventana (para el arranque con Windows)")
    args = p.parse_args()
    configurar_logs()

    if args.sin_ventana:
        import uvicorn

        from app.server.app import create_app

        uvicorn.run(create_app(tareas=True), host=args.host, port=args.port, log_config=None)
        return

    if args.reconfigurar:
        config_local.borrar()

    from app.desktop.window import abrir_ventana

    # oculta solo tiene sentido en Windows, donde hay icono de bandeja para volver a abrirla
    oculta = args.bandeja and sys.platform == "win32"
    abrir_ventana({"modo": CLIENTE, "url": args.cliente} if args.cliente else None, oculta)


if __name__ == "__main__":
    main()
