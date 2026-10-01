from types import SimpleNamespace

import pytest

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy
from app.server.domain import estados as E
from app.server.domain.fechas_letras import fecha_larga, fecha_letras
from app.server.domain.plantillas import TIPO_CONSTANCIA, TIPO_PASE, fecha_doc, fill_tpl
from app.server.domain.rutas import paso_cerrado, siguiente_paso
from tests.conftest import calendario_de_js, f, golden, iso

G = golden("escenarios.json")
CAMPOS = (
    "R={{radicado}}|F={{radicado_full}}|P={{proceso}}|DTE={{demandante}}|DDA={{demandado}}|CU={{cuaderno}}"
    "|D={{descripcion}}|M={{materia}}|T={{termino}}|FI={{fecha_inicio}}|V={{vencimiento}}|MP={{motivo_pase}}"
    "|FE={{fecha}}|FL={{fecha_letras}}|C={{ciudad}}|R2={{radicado}}"
)


class Escenario:
    def __init__(self, e):
        self.e = e
        self.ctx = E.Contexto(
            hoy=f(e["hoy"]),
            calendario=calendario_de_js(G["festivos"], e["calendario"]),
            terminos={t["n"]: E.TerminoInfo(t["d"], t.get("h") is not False) for t in e["terminos"]},
        )
        self.rutas = {r["id"]: SimpleNamespace(id=r["id"], pasos=[SimpleNamespace(**p) for p in r["pasos"]]) for r in e["rutas"]}
        self.procesos = {p["id"]: proceso_desde_legacy(p) for p in e["procesos"]}
        self.casos = [(actuacion_desde_legacy(x["a"]), x) for x in e["acts"]]
        self.acts = [a for a, _ in self.casos]

    def de_proceso(self, pid):
        return [a for a in self.acts if a.proceso_id == pid]


ESCENARIOS = [Escenario(e) for e in G["escenarios"]]
IDS = [f"{e.e['hoy']}#{i}" for i, e in enumerate(ESCENARIOS)]
por_escenario = pytest.mark.parametrize("esc", ESCENARIOS, ids=IDS)


def test_etiquetas():
    assert list(E.SIT) == G["sit"]
    assert list(E.SIT_BADGE) == G["sitBadge"]


@por_escenario
def test_actuaciones(esc):
    assert len(esc.casos) == 43
    for a, x in esc.casos:
        d = a.descripcion
        c = E.codigo(a, esc.ctx)
        assert c == x["codigo"], d
        assert iso(E.fecha_activa(a, esc.ctx)) == x["fechaActiva"], d
        assert iso(E.vencimiento(a, esc.ctx)) == x["vencimiento"], d
        assert E.est_termino(a, esc.ctx) == x["estTermino"], d
        assert E.dias_estado(a, c, esc.ctx) == x["diasEstado"], d
        assert E.ubicacion(c) == x["ubicacion"], d
        assert list(E.resultado(a, c, esc.ctx)) == x["resultado"], d
        assert paso_cerrado(a, esc.ctx) == x["pasoCerrado"], d


@por_escenario
def test_siguiente_paso(esc):
    for a, x in esc.casos:
        s = siguiente_paso(a, esc.de_proceso(a.proceso_id), esc.rutas)
        obtenido = {"ruta": s.ruta.id, "idx": s.idx, "nombre": s.paso.nombre} if s else None
        assert obtenido == x["siguiente"], a.descripcion


@por_escenario
def test_procesos(esc):
    for x in esc.e["procs"]:
        p = esc.procesos[x["id"]]
        d = E.proc_deriv(p.situacion, esc.de_proceso(p.id), esc.ctx)
        obtenido = {
            "id": p.id, "vivas": d.vivas, "repD": d.rep_despacho, "repS": d.rep_secretaria, "enSec": d.en_secretaria,
            "enDes": d.en_despacho, "inact": d.inactividad, "prox": iso(d.proximo), "diasSin": d.dias_sin_mov,
        }  # fmt: skip
        assert obtenido == x, p.radicado


@por_escenario
def test_tablero(esc):
    s, x = E.global_stats(esc.acts, esc.ctx), esc.e["stats"]
    assert (s["sin_constancia"], s["falta_pasar"], s["al_despacho"]) == (x["sc"], x["fp"], x["ad"])
    assert s["por_situacion"] == x["ps"]
    assert (s["en_despacho"], s["en_secretaria"]) == (x["eD"], x["eS"])
    obtenido = sorted((iso(fe), esc.procesos[a.proceso_id].radicado, a.descripcion) for fe, a in s["proximos"])
    assert obtenido == sorted((p["f"], p["rad"], p["desc"]) for p in x["prox"])
    assert [fe for fe, _ in s["proximos"]] == sorted(fe for fe, _ in s["proximos"])


@por_escenario
def test_documentos(esc):
    cfg = esc.e["config"]
    for a, x in esc.casos:
        p = esc.procesos[a.proceso_id]
        assert iso(fecha_doc(a, TIPO_CONSTANCIA, esc.ctx)) == x["fechaConstancia"], a.descripcion
        assert iso(fecha_doc(a, TIPO_PASE, esc.ctx)) == x["fechaPase"], a.descripcion
        assert fill_tpl(CAMPOS, a, p, esc.ctx, motivo="Recurso", **cfg) == x["textoHoy"]
        assert fill_tpl(CAMPOS, a, p, esc.ctx, fecha=f("2027-01-21"), **cfg) == x["textoFecha"]


def test_fechas_en_letras():
    for s, larga, letras in golden("fechas.json"):
        assert fecha_larga(f(s)) == larga
        assert fecha_letras(f(s)) == letras
