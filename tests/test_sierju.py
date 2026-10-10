"""La derivación completa de la estadística SIERJU, comparada evento por evento contra la v2."""

import io
import re
import zipfile

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy, stat_evento_desde_legacy
from app.server.domain.sierju import eventos as EV
from app.server.domain.sierju import matrices as MX
from app.server.db.seeds import cargar_mapa_plantilla
from app.server.services import sierju_excel as XL
from tests.conftest import f, golden, iso

G = golden("v2_sierju.json")
DESDE, HASTA = f(G["periodo"]["desde"]), f(G["periodo"]["hasta"])


def _base():
    procesos = [proceso_desde_legacy(p) for p in G["db"]["procesos"]]
    # el modelo guarda las solicitudes por relación; aquí basta con la lista en el orden del respaldo
    actuaciones = [actuacion_desde_legacy(a) for a in G["db"]["actuaciones"]]
    manuales = [stat_evento_desde_legacy(e) for e in G["db"]["statEventos"]]
    return procesos, actuaciones, manuales


def _paquete():
    procesos, actuaciones, manuales = _base()
    return EV.todos(procesos, actuaciones, manuales, DESDE, HASTA)


def _plano(e: EV.Evento) -> list:
    return [iso(e.fecha), e.seccion, e.fila, e.columna, e.cantidad, e.origen, e.proceso_id, e.nota]


def test_los_eventos_son_los_mismos_que_en_la_v2():
    obtenido = [_plano(e) for e in _paquete().eventos]
    esperado = [list(x) for x in G["eventos"]]
    # se comparan en orden: la v2 recorre procesos, luego actuaciones y luego los agregados
    assert len(obtenido) == len(esperado), f"{len(obtenido)} eventos contra {len(esperado)}"
    distintos = [(i, o, e) for i, (o, e) in enumerate(zip(obtenido, esperado)) if o != e]
    assert distintos == [], f"{len(distintos)} eventos divergen: {distintos[:3]}"


def test_los_avisos_son_los_mismos():
    p = _paquete()
    obtenido = [[iso(a.fecha) or "", a.seccion, a.proceso_id, a.nota] for a in p.avisos]
    assert obtenido == [list(x) for x in G["avisos"]]


def test_conteos_de_automaticos_y_manuales():
    p = _paquete()
    assert (p.automaticos, p.manuales) == (G["conteos"]["auto"], G["conteos"]["manual"])
    # el evento manual de 2025 queda fuera del periodo
    assert all(DESDE <= e.fecha <= HASTA for e in p.eventos)


def test_las_matrices_coinciden_celda_por_celda():
    obtenidas = MX.construir(_paquete())
    esperadas = G["matrices"]
    assert [m.seccion.code for m in obtenidas] == [x["code"] for x in esperadas]
    for m, esp in zip(obtenidas, esperadas):
        assert m.total == esp["total"], f"{m.seccion.code}: total {m.total} contra {esp['total']}"
        # solo se comparan las celdas con dato: la v2 crea la fila vacía igual que nosotros
        con_dato = {fila: cols for fila, cols in m.mapa.items() if cols}
        esperado = {fila: cols for fila, cols in esp["mapa"].items() if cols}
        assert con_dato == esperado, m.seccion.code


def test_hay_movimiento_en_las_secciones_que_importan():
    """Red de seguridad: si la clasificación se rompiera, todo saldría en cero y los test de arriba también."""
    por_seccion = {m.seccion.code: m.total for m in MX.construir(_paquete())}
    assert por_seccion["SEC4587"] > 0, "movimiento civil"
    assert por_seccion["SEC5959"] > 0, "control de garantías"
    assert por_seccion["SEC4603"] > 0, "audiencias civiles"
    assert por_seccion["SEC5414"] > 0, "audiencias penales"
    assert por_seccion["SEC4416"] > 0, "providencias"
    assert por_seccion["SEC5082"] > 0, "recursos interpuestos"
    assert por_seccion["SEC5083"] > 0, "recursos decididos"
    assert por_seccion["SEC5086"] > 0, "remate y amparo de pobreza"
    assert por_seccion["SEC5880"] > 0, "tutelas"
    assert por_seccion["SEC4777"] > 0, "trámite posterior por actuación"
    assert por_seccion["SEC5209"] > 0, "trámite posterior por proceso"


# ---------- Excel oficial ----------

# El arreglo de COL6828: la v2 creaba el evento pero el llenado descartaba la columna porque su etiqueta
# trae un salto de línea, y además el mapa de la plantilla no la tenía. Ahora sí se escribe.
COL6828 = {"SEC4603": "H", "SEC5414": "T"}

_RX_CELDA = re.compile(r'<c r="([A-Z]+\d+)"([^>]*?)(?:/>|>([\s\S]*?)</c>)', re.S)
_RX_S = re.compile(r'\s+s="(\d+)"')
_RX_V = re.compile(r"<v>([^<]*)</v>")
_RX_T = re.compile(r't="([^"]*)"')


def _celdas_de(xml: str) -> dict[str, dict]:
    out = {}
    for m in _RX_CELDA.finditer(xml):
        attrs, cuerpo = m[2] or "", m[3] or ""
        s = _RX_S.search(attrs)
        v = _RX_V.search(cuerpo)
        t = _RX_T.search(attrs)
        out[m[1]] = {"s": int(s[1]) if s else None, "v": v[1] if v else None, "t": t[1] if t else None}
    return out


def _excepciones_col6828() -> set[str]:
    """Las celdas de esa columna en cada hoja: es la única diferencia aceptada frente a la v2."""
    mapa = cargar_mapa_plantilla()["mapa"]
    refs = set()
    for code, letra in COL6828.items():
        for nro in mapa[code]["fil"].values():
            refs.add((mapa[code]["sheet"], f"{letra}{nro}"))
    return refs


def test_el_excel_oficial_queda_celda_por_celda_igual_que_en_la_v2():
    contenido, sin_destino = XL.llenar_plantilla(MX.construir(_paquete()))
    # con COL6828 en el mapa ya no queda ninguna columna con dato sin destino
    assert sin_destino == []

    excepciones = _excepciones_col6828()
    distintos = []
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombres = set(z.namelist())
        for hoja, esperado in G["excel"]["hojas"].items():
            ruta = f"xl/worksheets/{hoja}"
            assert ruta in nombres, ruta
            obtenido = _celdas_de(z.read(ruta).decode("utf-8"))
            assert set(obtenido) == set(esperado["celdas"]), f"{hoja}: cambió el número de celdas"
            for ref, esp in esperado["celdas"].items():
                if (hoja, ref) in excepciones:
                    continue
                if obtenido[ref] != esp:
                    distintos.append((hoja, ref, esp, obtenido[ref]))
    assert distintos == [], f"{len(distintos)} celdas divergen: {distintos[:5]}"


def test_col6828_ahora_si_llega_al_excel():
    """Era el bug de la columna perdida: el evento se creaba y la celda quedaba sin escribir."""
    paquete = _paquete()
    # en la base de prueba hay una audiencia civil aplazada por esa causa
    assert any("6828" in e.columna for e in paquete.eventos), "la base de prueba debe tener la causa de COL6828"
    contenido, _ = XL.llenar_plantilla(MX.construir(paquete))
    mapa = cargar_mapa_plantilla()["mapa"]["SEC4603"]
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        celdas = _celdas_de(z.read(f"xl/worksheets/{mapa['sheet']}").decode("utf-8"))
    con_dato = [c for nro in mapa["fil"].values() if (c := celdas.get(f"H{nro}")) and c["v"] not in (None, "0")]
    assert con_dato, "la columna H de SEC4603 debería tener el conteo de la causa"


def test_los_estilos_quedan_como_los_deja_la_v2():
    contenido, _ = XL.llenar_plantilla(MX.construir(_paquete()))
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        estilos = z.read("xl/styles.xml").decode("utf-8")
    esperado = G["excel"]["estilos"]
    assert int(re.search(r'<fills count="(\d+)">', estilos)[1]) == esperado["fills"]
    assert int(re.search(r'<cellXfs count="(\d+)">', estilos)[1]) == esperado["cellXfs"]
    assert ("FFFFF2CC" in estilos) is esperado["tieneRelleno"]


def test_el_archivo_abre_como_xlsx_y_conserva_todas_sus_partes():
    contenido, _ = XL.llenar_plantilla(MX.construir(_paquete()))
    with zipfile.ZipFile(XL.PLANTILLA_SIERJU) as origen, zipfile.ZipFile(io.BytesIO(contenido)) as nuevo:
        assert nuevo.namelist() == origen.namelist()
        assert nuevo.testzip() is None
    assert XL.nombre_archivo(DESDE, HASTA) == "SIERJU_2026-01-01_a_2026-12-31.xlsx"
