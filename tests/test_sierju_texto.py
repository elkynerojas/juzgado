"""El motor de clasificación difusa, comparado etiqueta por etiqueta contra la v2.

Es la pieza más delicada del port: si `mejor()` elige otra etiqueta que `statBest`, todas las secciones
quedan mal y el diagnóstico se vuelve imposible. Por eso se compara antes de construir nada encima.
"""

import pytest

from app.server.domain.sierju import secciones as SEC
from app.server.domain.sierju import texto as T
from tests.conftest import golden

G = golden("v2_sierju.json")


def test_normalizacion_de_textos():
    distintos = [(q, T.norm(q), esperado) for q, esperado in G["norm"] if T.norm(q) != esperado]
    assert distintos == []


def test_tokens():
    distintos = [(q, list(T.tokens(q)), esperado) for q, esperado in G["tokens"] if list(T.tokens(q)) != esperado]
    assert distintos == []


def test_la_mejor_etiqueta_es_la_misma_que_en_la_v2():
    distintos = []
    for code, cual, consulta, esperado in G["best"]:
        s = SEC.SECCIONES[code]
        obtenido = T.mejor(s.filas if cual == "rows" else s.columnas, consulta)
        if obtenido != esperado:
            distintos.append({"seccion": code, "en": cual, "consulta": consulta, "esperado": esperado, "obtenido": obtenido})
    assert distintos == [], f"{len(distintos)} de {len(G['best'])} comparaciones divergen: {distintos[:4]}"


def test_las_secciones_se_cargan_completas():
    esperado = {s["code"]: (s["n"], s["sheet"], s["title"], s["rows"], s["cols"]) for s in G["secciones"]}
    obtenido = {c: (s.n, s.sheet, s.title, len(s.filas), len(s.columnas)) for c, s in SEC.SECCIONES.items()}
    assert obtenido == esperado


def test_solo_las_secciones_de_la_plantilla_llegan_al_excel():
    """Las otras ocho existen y generan eventos, pero el formato oficial no tiene dónde ponerlas."""
    assert [s.code for s in SEC.ACTIVAS] == sorted(G["activas"], key=lambda c: next(x["n"] for x in G["secciones"] if x["code"] == c))
    assert set(G["activas"]) <= set(SEC.SECCIONES)
    assert len(SEC.ACTIVAS) == 23 and len(SEC.SECCIONES) == 31


def test_el_prefijo_se_limpia_igual_de_estricto_que_en_la_v2():
    assert T.limpiar("(FIL4207) ARTÍCULO 120. LESIONES CULPOSAS.") == "ARTÍCULO 120. LESIONES CULPOSAS."
    # la etiqueta de COL6828 trae un salto de línea dentro del paréntesis: la v2 no lo limpia y aquí tampoco,
    # para no mover las puntuaciones. Solo se limpia al presentarla.
    rota = "(COL6828\n) POR CAUSA DEL JUEZ O MAGISTRADO-AJENAS AL FUNCIONARIO"
    assert T.limpiar(rota) == rota
    assert T.para_mostrar(rota) == "POR CAUSA DEL JUEZ O MAGISTRADO-AJENAS AL FUNCIONARIO"


@pytest.mark.parametrize("code", ["SEC4603", "SEC5414"])
def test_col6828_se_encuentra_por_codigo(code):
    """La columna que la v2 perdía: la etiqueta tiene el salto de línea y el llenado la descartaba."""
    assert SEC.columna_por_codigo(code, "COL6828")
    assert "6828" in SEC.columna_por_codigo(code, "COL6828")


def test_busqueda_de_columna_con_alias():
    """statFindCol reintenta con los alias del formato cuando el texto no engancha directo."""
    distintos = []
    for code, consulta, esperado in G["findCol"]:
        obtenido = SEC.buscar_columna(code, consulta)
        if obtenido != esperado:
            distintos.append({"seccion": code, "consulta": consulta, "esperado": esperado, "obtenido": obtenido})
    assert distintos == [], f"{len(distintos)} de {len(G['findCol'])} divergen: {distintos[:4]}"


def test_busqueda_de_fila_con_respaldo_en_otros():
    distintos = []
    for code, consulta, esperado in G["findRow"]:
        obtenido = SEC.buscar_fila(code, consulta)
        if obtenido != esperado:
            distintos.append({"seccion": code, "consulta": consulta, "esperado": esperado, "obtenido": obtenido})
    assert distintos == [], f"{len(distintos)} de {len(G['findRow'])} divergen: {distintos[:4]}"
