import json
import socket
import urllib.request
from urllib.parse import urlsplit

from app.desktop.config_local import PUERTO


def normalizar_url(texto: str) -> str:
    """Acepta '192.168.1.10', 'servidor:8765' o una URL completa."""
    texto = texto.strip()
    if not texto:
        raise ValueError("Escriba la dirección del servidor")
    if "://" not in texto:
        texto = "http://" + texto
    partes = urlsplit(texto)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise ValueError("Dirección no válida")
    try:
        puerto = partes.port
    except ValueError:
        raise ValueError("Puerto no válido") from None
    host = f"[{partes.hostname}]" if ":" in partes.hostname else partes.hostname
    return f"{partes.scheme}://{host}:{puerto or PUERTO}"


def responde(url: str, timeout: float = 3.0) -> bool:
    """True si en esa dirección hay un servidor de Control de Procesos."""
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=timeout) as r:
            return json.loads(r.read()).get("status") == "ok"
    except (OSError, ValueError):
        return False


def puerto_libre(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", puerto))
            return True
        except OSError:
            return False


def direcciones_lan() -> list[str]:
    """IPs de este equipo en la red local, la principal primero."""
    ips: list[str] = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            # no envía nada: solo averigua por qué interfaz saldría el tráfico
            s.connect(("10.255.255.255", 1))
            ips.append(s.getsockname()[0])
        except OSError:
            pass
    try:
        ips.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return [ip for ip in dict.fromkeys(ips) if not ip.startswith("127.")]
