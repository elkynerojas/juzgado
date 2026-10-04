"""Datos de la aplicación para «Ayuda → Acerca de» y el instalador.

Son constantes y no importlib.metadata porque el ejecutable de PyInstaller no lleva los metadatos
del paquete. tests/test_acerca.py verifica que la versión coincida con pyproject.toml y el instalador.
"""

NOMBRE = "Control de Procesos"
VERSION = "1.1"
DESARROLLADOR = {
    "nombre": "RedSoft Developers",
    "telefono": "+57 318 220 41 90",
    "correo": "redsoftdevelopers@gmail.com",
}
