"""Genera packaging/icono.ico a partir del mismo dibujo del icono de bandeja."""

from pathlib import Path

from app.desktop.bandeja import _imagen

destino = Path(__file__).resolve().parent / "icono.ico"
_imagen().resize((256, 256)).save(destino, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(destino)
