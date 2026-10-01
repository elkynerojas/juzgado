"""Icono en la bandeja de Windows: el servidor sigue atendiendo a los clientes con la ventana cerrada."""

import logging
import sys

log = logging.getLogger(__name__)


def _imagen():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 62, 62), radius=12, fill=(31, 56, 100, 255))
    # balanza simplificada
    d.rectangle((30, 14, 34, 48), fill="white")
    d.rectangle((14, 16, 50, 20), fill="white")
    d.rectangle((22, 46, 42, 50), fill="white")
    d.pieslice((8, 22, 26, 40), 0, 180, fill="white")
    d.pieslice((38, 22, 56, 40), 0, 180, fill="white")
    return img


def instalar(window, direccion: str) -> bool:
    """Devuelve True si quedó la bandeja activa (solo Windows)."""
    if sys.platform != "win32":
        return False
    try:
        import pystray
    except ImportError:
        log.warning("pystray no está instalado; la aplicación se cerrará con la ventana")
        return False

    estado = {"saliendo": False}

    def abrir(icono=None, item=None):
        window.show()
        window.restore()

    def salir(icono, item):
        estado["saliendo"] = True
        icono.stop()
        window.destroy()

    def al_cerrar():
        if estado["saliendo"]:
            return True
        window.hide()
        icono.notify("El servidor sigue funcionando. Para cerrarlo use «Salir» en este icono.", "Control de Procesos")
        return False  # cancela el cierre

    icono = pystray.Icon(
        "control-procesos",
        _imagen(),
        "Control de Procesos (servidor)",
        menu=pystray.Menu(
            pystray.MenuItem("Abrir", abrir, default=True),
            pystray.MenuItem(f"Dirección para los clientes: {direccion}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir y detener el servidor", salir),
        ),
    )
    window.events.closing += al_cerrar
    icono.run_detached()
    return True
