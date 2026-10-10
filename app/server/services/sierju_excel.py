"""Llena la plantilla oficial del SIERJU conservando su formato (puerto de `doFillTemplate` de la v2).

No hay librería de Excel: la plantilla es un .xlsx, o sea un ZIP de XML. Se reescriben las celdas de datos
una por una y se vuelve a empaquetar, de modo que estilos, encabezados y fórmulas quedan intactos.
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date

from app.server.db.seeds import PLANTILLA_SIERJU, cargar_mapa_plantilla
from app.server.domain.sierju.matrices import MatrizSeccion
from app.server.domain.sierju.secciones import RX_COL, RX_FIL

# columnas que el formato calcula solo: se les deja el estilo pero no el valor
SUPRIMIDAS = {
    "SEC4603": ("COL4713", "COL4716", "COL4717"),
    "SEC5414": ("COL4716", "COL4717"),
}

RELLENO = '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/><bgColor indexed="64"/></patternFill></fill>'

_RX_FILLS = re.compile(r'<fills count="(\d+)">')
_RX_CELLXFS = re.compile(r'<cellXfs count="(\d+)">([\s\S]*?)</cellXfs>', re.S)
_RX_XF = re.compile(r"<xf\b[^>]*/>|<xf\b[^>]*>[\s\S]*?</xf>", re.S)
_RX_FILLID = re.compile(r'\s+fillId="\d+"')
_RX_APPLYFILL = re.compile(r'\s+applyFill="[^"]*"')
_RX_CELDA = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>[\s\S]*?</c>)', re.S)
_RX_TEXTO = re.compile(r't="(?:s|str|inlineStr)"')
_RX_S = re.compile(r'\s+s="(\d+)"')
_RX_QUITAR = re.compile(r'\s+t="[^"]*"|\s+s="[^"]*"')


@dataclass
class Valores:
    """Lo que se va a escribir, por hoja: celda -> cantidad, y las celdas a dejar en blanco."""

    celdas: dict[str, dict[str, int]] = field(default_factory=dict)
    suprimidas: dict[str, set[str]] = field(default_factory=dict)
    # columnas con dato que la plantilla no sabe dónde poner; se reportan en vez de perderse
    sin_destino: list[str] = field(default_factory=list)


def valores(matrices: list[MatrizSeccion]) -> Valores:
    mapa = cargar_mapa_plantilla()["mapa"]
    out = Valores()
    for m in matrices:
        info = mapa.get(m.seccion.code)
        if not info:
            continue
        celdas = out.celdas.setdefault(info["sheet"], {})
        for fila, columnas in m.mapa.items():
            mf = RX_FIL.search(fila)
            if not mf:
                continue
            nro = info["fil"].get(f"FIL{mf[1]}")
            if not nro:
                continue
            for col, cantidad in columnas.items():
                mc = RX_COL.search(col)
                if not mc:
                    continue
                letra = info["col"].get(f"COL{mc[1]}")
                if not letra:
                    if cantidad:
                        out.sin_destino.append(f"{m.seccion.code}/COL{mc[1]}")
                    continue
                celdas[f"{letra}{nro}"] = cantidad

    for code, columnas in SUPRIMIDAS.items():
        info = mapa.get(code)
        if not info:
            continue
        skip = out.suprimidas.setdefault(info["sheet"], set())
        for cc in columnas:
            letra = info["col"].get(cc)
            if not letra:
                continue
            skip.update(f"{letra}{nro}" for nro in info["fil"].values())
    return out


def _parchar_estilos(xml: str) -> tuple[str, int | None]:
    """Triplica los estilos: los originales, una copia en blanco y una sombreada para las celdas con dato."""
    fm = _RX_FILLS.search(xml)
    if not fm:
        return xml, None
    n_fills = int(fm[1])
    xml = xml.replace("</fills>", RELLENO + "</fills>", 1)
    xml = _RX_FILLS.sub(f'<fills count="{n_fills + 1}">', xml, count=1)

    cm = _RX_CELLXFS.search(xml)
    if not cm:
        return xml, None
    n_xf, cuerpo = int(cm[1]), cm[2]
    xfs = _RX_XF.findall(cuerpo)

    def variante(xf: str, fill_id: int) -> str:
        limpio = _RX_APPLYFILL.sub("", _RX_FILLID.sub("", xf))
        return limpio.replace("<xf", f'<xf fillId="{fill_id}" applyFill="1"', 1)

    blancos = "".join(variante(x, 0) for x in xfs)
    sombreados = "".join(variante(x, n_fills) for x in xfs)
    xml = _RX_CELLXFS.sub(
        lambda _: f'<cellXfs count="{n_xf * 3}">{cuerpo}{blancos}{sombreados}</cellXfs>', xml, count=1
    )
    return xml, n_xf


def _parchar_hoja(xml: str, celdas: dict[str, int], min_row: int, skip: set[str], base: int | None) -> str:
    """Reescribe las celdas de datos. No toca la columna A, los encabezados ni nada que sea texto."""

    def reemplazo(m: re.Match) -> str:
        col, fila, attrs = m[1], int(m[2]), m[3]
        if col == "A" or fila < min_row:
            return m[0]
        if _RX_TEXTO.search(attrs):
            return m[0]
        ref = f"{col}{fila}"
        sm = _RX_S.search(attrs)
        orig = int(sm[1]) if sm else 0
        resto = _RX_QUITAR.sub("", attrs)
        blanco = base + orig if base is not None else orig
        sombreado = 2 * base + orig if base is not None else orig
        if ref in skip:
            return f'<c r="{ref}" s="{blanco}"{resto}/>'
        v = celdas.get(ref, 0)
        estilo = sombreado if v else blanco
        return f'<c r="{ref}" s="{estilo}"{resto}><v>{v}</v></c>'

    return _RX_CELDA.sub(reemplazo, xml)


def nombre_archivo(desde: date, hasta: date) -> str:
    return f"SIERJU_{desde.isoformat()}_a_{hasta.isoformat()}.xlsx"


def llenar_plantilla(matrices: list[MatrizSeccion]) -> tuple[bytes, list[str]]:
    """Devuelve el .xlsx completo y la lista de columnas con dato que la plantilla no supo ubicar."""
    tpl = cargar_mapa_plantilla()
    mapa, hojas = tpl["mapa"], tpl["hojas"]
    v = valores(matrices)

    with zipfile.ZipFile(PLANTILLA_SIERJU) as origen:
        partes = [(i.filename, origen.read(i.filename)) for i in origen.infolist()]

    base = None
    estilos = None
    for nombre, datos in partes:
        if nombre.endswith("styles.xml"):
            estilos, base = _parchar_estilos(datos.decode("utf-8"))
            break

    salida = io.BytesIO()
    # se reescribe en el mismo orden y con fecha fija para que el archivo sea reproducible
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in partes:
            if nombre.endswith("styles.xml") and estilos is not None:
                datos = estilos.encode("utf-8")
            else:
                hoja = nombre.split("/")[-1]
                code = hojas.get(hoja)
                if code and "worksheets/" in nombre:
                    xml = _parchar_hoja(
                        datos.decode("utf-8"),
                        v.celdas.get(hoja, {}),
                        mapa[code]["minRow"],
                        v.suprimidas.get(hoja, set()),
                        base,
                    )
                    datos = xml.encode("utf-8")
            info = zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, datos)
    return salida.getvalue(), sorted(set(v.sin_destino))


# ---------- libro genérico (sin plantilla) ----------

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{hojas}</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _escapar(v) -> str:
    return str(v or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _letra(n: int) -> str:
    """1 -> A, 27 -> AA."""
    out = ""
    while n > 0:
        n, resto = divmod(n - 1, 26)
        out = chr(65 + resto) + out
    return out


def _texto(fila: int, col: int, v) -> str:
    return f'<c r="{_letra(col)}{fila}" t="inlineStr"><is><t>{_escapar(v)}</t></is></c>'


def _numero(fila: int, col: int, v) -> str:
    return f'<c r="{_letra(col)}{fila}"><v>{int(v or 0)}</v></c>'


def libro_generico(matrices: list[MatrizSeccion], desde: date, hasta: date) -> bytes:
    """Un .xlsx propio, una hoja por sección: sirve para revisar los datos sin la plantilla oficial."""
    hojas, nombres = [], []
    for i, m in enumerate(matrices, 1):
        sec = m.seccion
        nombres.append(f"{sec.n} {sec.code}"[:31])
        filas = [f'<row r="1">{_texto(1, 1, sec.title)}</row>']
        filas.append(f'<row r="2">{_texto(2, 1, "Periodo")}{_texto(2, 2, f"{desde.isoformat()} a {hasta.isoformat()}")}</row>')
        encabezado = _texto(3, 1, "TIPOS PROCESOS") + "".join(_texto(3, j + 2, c) for j, c in enumerate(sec.columnas))
        filas.append(f'<row r="3">{encabezado}</row>')
        for k, fila in enumerate(sec.filas, 4):
            celdas = _texto(k, 1, fila) + "".join(
                _numero(k, j + 2, m.mapa.get(fila, {}).get(c, 0)) for j, c in enumerate(sec.columnas)
            )
            filas.append(f'<row r="{k}">{celdas}</row>')
        dim = f"A1:{_letra(len(sec.columnas) + 1)}{len(sec.filas) + 3}"
        hojas.append(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="{dim}"/><sheetData>{"".join(filas)}</sheetData></worksheet>'
        )

    refs = "".join(f'<sheet name="{_escapar(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(nombres, 1))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{refs}</sheets></workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(hojas) + 1)
        )
        + "</Relationships>"
    )
    tipos = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(hojas) + 1)
    )

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CT.format(hojas=tipos))
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        for i, xml in enumerate(hojas, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", xml)
    return salida.getvalue()


def nombre_generico(desde: date, hasta: date) -> str:
    return f"SIERJU_COMPLETO_{desde.isoformat()}_{hasta.isoformat()}.xlsx"
