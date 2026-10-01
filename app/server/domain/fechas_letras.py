from datetime import date

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip
_UNIDADES = ("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
_DECENAS = ("", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_ESPECIALES = {
    11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince", 16: "dieciséis", 17: "diecisiete",
    18: "dieciocho", 19: "diecinueve", 21: "veintiuno", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro",
    25: "veinticinco", 26: "veintiséis", 27: "veintisiete", 28: "veintiocho", 29: "veintinueve",
}  # fmt: skip


def decenas_letras(n: int) -> str:
    if n < 10:
        return _UNIDADES[n]
    if n in _ESPECIALES:
        return _ESPECIALES[n]
    d, u = divmod(n, 10)
    return _DECENAS[d] + (" y " + _UNIDADES[u] if u else "")


def anio_letras(anio: int) -> str:
    resto = anio - 2000
    return "dos mil" + (" " + decenas_letras(resto) if resto else "")


def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_letras(d: date) -> str:
    return f"{decenas_letras(d.day)} ({d.day}) de {MESES[d.month - 1]} de {anio_letras(d.year)} ({d.year})"
