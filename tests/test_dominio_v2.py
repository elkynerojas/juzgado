"""Reglas de la v2 del HTML portadas a Python, comparadas contra tests/golden/v2_dominio.json.

Donde la v2 tenía un error que se corrigió al portar, el valor esperado se ajusta aquí y queda comentado.
"""

import re
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy
from app.server.domain import automatismos as A
from app.server.domain import estados as E
from app.server.domain import naturaleza as N
from app.server.domain.secretaria import (
    CIERRE_EJECUTORIA,
    CIERRE_PROVIDENCIA,
    autocompletar_actuacion,
    ejecutoria,
    fecha_gestion_secretaria,
)
from tests.conftest import calendario_de_js, f, golden, iso

G = golden("v2_dominio.json")
CALS = [calendario_de_js(G["festivos"], g["calendario"]) for g in G["gestion"]]


@pytest.mark.parametrize("x", G["naturalezas"], ids=[x["nat"] for x in G["naturalezas"]])
def test_listas_por_naturaleza(x):
    n = x["nat"]
    assert (N.es_penal(n), N.es_garantias(n), N.es_conocimiento(n), N.es_constitucional(n)) == (
        x["esPenal"], x["esGarantias"], x["esConocimiento"], x["esConstitucional"],
    )  # fmt: skip
    assert N.lista_sierju(n) == x["listaSierju"]
    assert N.lista_salidas(n) == x["listaSalidas"]
    assert N.penal_solicitudes(n) == x["penalSolicitudes"]
    assert N.entradas_sierju(n) == x["entradasSierju"]
    assert N.salidas_act(n) == x["salidasAct"]
    # la v2 repetía opciones (p. ej. "Oficio" en tutela); aquí van una sola vez y en el mismo orden
    assert N.tipos_gestion(n, G["tiposSolicitud"]) == list(dict.fromkeys(x["tiposGestion"]))


def test_naturaleza_penal_compuesta():
    assert N.componer_naturaleza("1826", N.CONOCIMIENTO) == "Penal 1826 - Conocimiento"
    with pytest.raises(ValueError):
        N.componer_naturaleza("1098", N.GARANTIAS)  # la v2 nunca la ofrecía en el formulario


@pytest.mark.parametrize("procedimiento", ["Garantías", "Conocimiento"])
def test_delitos_unificados_en_el_orden_de_la_v2(procedimiento):
    assert [list(x) for x in N.delitos_unificados(procedimiento)] == G["delitos"][procedimiento]


def test_sugerencia_de_tipo_sierju():
    malos = [(c, n, r, N.sug_sierju(c, n)) for c, n, r in G["sug"] if N.sug_sierju(c, n) != r]
    assert malos == []
    # la v2 trataba "Incidente de desacato" como civil; se clasifica igual que "Desacato"
    for c, n, r in G["sug"]:
        if n == "Desacato":
            assert N.sug_sierju(c, N.DESACATO) == r, c


@pytest.mark.parametrize("i", range(len(G["gestion"])))
def test_fecha_gestion_secretaria(i):
    g = G["gestion"][i]
    desde = f(g["desde"])
    obtenido = [iso(fecha_gestion_secretaria(desde + timedelta(days=k), CALS[i])) for k in range(len(g["fechas"]))]
    assert obtenido == g["fechas"]
    assert fecha_gestion_secretaria(None, CALS[i]) is None


def _act(**kw):
    base = dict(
        notif_fecha=None, ejec_dias=3, recurso_tipo="", superior_resultado="", superior_fecha=None, rec_impug="",
        rec_impug_result="", rec_impug_fecha=None, fecha_memorial=None, origen="Memorial", constancia=None, pasa="",
        pase=None, providencia=None, ejecutoria=None, cumplida=None, modo_cierre="",
    )  # fmt: skip
    return SimpleNamespace(**(base | kw))


def test_ejecutoria():
    for e in G["ejecutoria"]:
        r = e["recurso"]
        a = _act(
            notif_fecha=f(e["notif"]), ejec_dias=e["dias"], recurso_tipo=r[0], superior_resultado=r[1],
            superior_fecha=f(r[2]), rec_impug=r[3], rec_impug_result=r[4], rec_impug_fecha=f(r[5]),
            ejecutoria=f(e["previa"]),
        )  # fmt: skip
        x = ejecutoria(a, CALS[e["cal"]])
        assert (x.estado, x.pendiente) == (e["estado"], e["pendiente"]), e
        # el formulario de la v2 llenaba la ejecutoria solo si estaba vacía
        autocompletar_actuacion(a, CALS[e["cal"]])
        assert iso(a.ejecutoria) == (e["ejecutoria"] or None), e


def test_autocompletar_actuacion():
    cal = CALS[1]
    # memorial radicado el sábado de la suspensión: la secretaría gestiona el primer hábil
    a = _act(fecha_memorial=date(2026, 9, 19), pasa="Sí")
    autocompletar_actuacion(a, cal)
    assert a.constancia == a.pase == date(2026, 9, 28)
    a = _act(fecha_memorial=date(2026, 9, 19), pasa="No – trámite secretaría", constancia=date(2026, 9, 20))
    autocompletar_actuacion(a, cal)
    assert (a.constancia, a.pase) == (date(2026, 9, 20), None)
    a = _act(fecha_memorial=date(2026, 9, 19), origen=E.ORIGEN_VENCIMIENTO, pasa="Sí")
    autocompletar_actuacion(a, cal)
    assert (a.constancia, a.pase) == (None, None)
    a = _act(providencia=date(2026, 10, 2), modo_cierre=CIERRE_PROVIDENCIA)
    autocompletar_actuacion(a, cal)
    assert a.cumplida == date(2026, 10, 2)
    a = _act(notif_fecha=date(2026, 10, 2), modo_cierre=CIERRE_EJECUTORIA)
    autocompletar_actuacion(a, cal)
    assert a.cumplida == a.ejecutoria == date(2026, 10, 7)
    a = _act(providencia=date(2026, 10, 2), modo_cierre=CIERRE_EJECUTORIA)
    autocompletar_actuacion(a, cal)
    assert a.cumplida is None


def test_tablero_con_ejecutorias():
    x = G["stats"]
    ctx = E.Contexto(
        hoy=f(x["hoy"]),
        calendario=calendario_de_js(G["festivos"], x["calendario"]),
        terminos={t["n"]: E.TerminoInfo(t["d"], t.get("h") is not False) for t in G["terminos"]},
    )
    radicados = {p["id"]: p["radicado"] for p in x["procesos"]}
    s = E.global_stats([actuacion_desde_legacy(a) for a in x["acts"]], ctx)
    obtenido = sorted((iso(fe), radicados[a.proceso_id], desc) for fe, a, desc in s["proximos"])
    assert obtenido == sorted((p["f"], p["rad"], p["desc"]) for p in x["prox"])
    assert any(d.startswith("Ejecutoria/recursos") for *_, d in s["proximos"])


# ---------- automatismos ----------

# la v2 guardaba causas que no existen en la estadística (bug #1 del plan)
CAUSA_CORREGIDA = {
    "Retiro de solicitud por el fiscal": A.CAUSA_RETIRO_FISCAL,
    "Retiro por solicitud de las demás partes": A.CAUSA_RETIRO_PARTES,
}


def _camel(k: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", k).lower()


def _plano(v):
    if v in (None, ""):
        return ""
    return v.isoformat() if isinstance(v, date) else v


def _esperado(js: dict) -> dict:
    out = {}
    for k, v in js.items():
        # la v2 dejaba audEstado "Programada" en actuaciones que no son audiencias; aquí quedan vacías
        if k.startswith("aud") and not js.get("esAudiencia"):
            continue
        if k == "audCausa":
            v = CAUSA_CORREGIDA.get(v, v)
        out[_camel(k)] = _plano(v)
    return out


def _obtenido(a, claves) -> dict:
    return {k: _plano(getattr(a, k)) for k in claves}


@pytest.mark.parametrize("caso", G["automatismos"], ids=[c["nombre"] for c in G["automatismos"]])
def test_automatismos_al_guardar_proceso(caso):
    p = proceso_desde_legacy(caso["proceso"])
    acts = [actuacion_desde_legacy(a) for a in caso["antes"]]
    terminos = {t["n"] for t in G["terminos"]}
    nuevas = A.al_guardar_proceso(p, acts, CALS[0], terminos, nuevo=caso["accion"] == "nuevo", crear_inicial=caso["crear"])
    resultado = acts + nuevas
    assert len(resultado) == len(caso["despues"])
    for a, js in zip(resultado, caso["despues"]):
        esperado = _esperado(js)
        assert _obtenido(a, esperado) == esperado, js["descripcion"]
    assert all(len(a.id) == 32 and a.proceso_id == p.id for a in nuevas)


def test_garantias_sin_solicitudes_ni_fecha():
    p = proceso_desde_legacy({"id": "p", "naturaleza": "Penal 906 - Garantías", "solicitudesPenales": []})
    [a] = A.al_guardar_proceso(p, [], CALS[0], set(), nuevo=True)
    assert (a.descripcion, a.fecha_memorial, a.constancia) == ("Se radican solicitud de control de garantías", None, None)
    assert A.sync_audiencia_cancelada(p, [a]) == []


def test_siguiente_cuaderno_incidente():
    assert A.siguiente_cuaderno_incidente("Incidente", ["Principal", "Incidente de desacato 4"]) == "Incidente 1"
    assert A.siguiente_cuaderno_incidente("Incidente", ["incidente 2", "Incidente 10", "Incidente x"]) == "Incidente 11"
    assert A.siguiente_cuaderno_incidente("Incidente de desacato", ["Incidente de desacato 1", "Incidente 7"]) == "Incidente de desacato 2"


# ---------- normalización de saveProc ----------

# campos del proceso que normalizar_proceso toca (los demás los copia el formulario tal cual)
NORMALIZADOS = (
    "fecha_terminacion", "fecha_archivo", "fecha_tramite_posterior", "cuadernos",
    "clase", "delitos_adicionales", "forma_salida", "solicitud_penal", "cuaderno_inicial",
)  # fmt: skip
HOY = date(2026, 9, 30)  # la fecha fija del generador


@pytest.mark.parametrize("caso", G["normalizacion"], ids=[c["nombre"] for c in G["normalizacion"]])
def test_normalizar_proceso(caso):
    js = caso["proceso"]
    p = proceso_desde_legacy(js)
    # el formulario manda los cuadernos y la fecha del trámite posterior sin resolver todavía
    p.cuadernos = []
    p.fecha_terminacion = f(caso["entrada"]["campos"].get("p_fterm"))
    p.fecha_archivo = f(caso["entrada"]["campos"].get("p_farch"))
    p.fecha_tramite_posterior = f(caso["entrada"]["campos"].get("p_tpfecha"))
    p.clase = caso["entrada"]["campos"].get("p_clase", "Ejecutivo")
    p.delitos_adicionales = list(caso["entrada"]["delitos"])
    p.forma_salida = caso["entrada"]["campos"].get("p_salida", "")
    p.solicitud_penal = ""
    for s in p.solicitudes_penales:
        s.fecha = None  # el formulario las manda sin fecha propia; la toma de la radicación

    A.normalizar_proceso(p, HOY, crear_medidas=caso["entrada"]["campos"].get("p_crearmed") == "Sí")

    esperado = {k: _plano(f(js[_js(k)]) if k.startswith("fecha") else js[_js(k)]) for k in NORMALIZADOS}
    assert {k: _plano(getattr(p, k)) for k in NORMALIZADOS} == esperado
    assert [_plano(s.fecha) for s in p.solicitudes_penales] == [_plano(f(s["fecha"])) for s in js["solicitudesPenales"]]


def _js(k: str) -> str:
    """fecha_terminacion -> fechaTerminacion"""
    cabeza, *resto = k.split("_")
    return cabeza + "".join(x.capitalize() for x in resto)
