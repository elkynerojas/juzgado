from datetime import date, timedelta

import pytest

from app.server.domain.calendario import Calendario, calc_venc, es_habil
from tests.conftest import calendario_de_js, f, golden, iso

G = golden("calendario.json")
CASOS = [(calendario_de_js(G["festivos"], c["calendario"]), c) for c in G["casos"]]


@pytest.mark.parametrize("cal,caso", CASOS, ids=["sin_excepciones", "con_excepciones"])
def test_dias_habiles_igual_al_original(cal, caso):
    d = f(caso["desde"])
    for i, esperado in enumerate(caso["habiles"]):
        dia = d + timedelta(days=i)
        assert es_habil(dia, cal) == (esperado == "1"), dia


@pytest.mark.parametrize("cal,caso", CASOS, ids=["sin_excepciones", "con_excepciones"])
def test_vencimientos_igual_al_original(cal, caso):
    for ini, dias, habil, esperado in caso["venc"]:
        assert iso(calc_venc(f(ini), dias, habil, cal)) == esperado, (ini, dias, habil)


def test_reglas_basicas():
    cal = Calendario(
        festivos=frozenset({date(2026, 10, 12)}),
        suspensiones=((date(2026, 9, 14), date(2026, 9, 18)),),
        cerrados=frozenset({date(2026, 10, 1)}),
    )
    assert not es_habil(date(2026, 10, 3), cal)  # sábado
    assert not es_habil(date(2026, 10, 12), cal)  # festivo
    assert not es_habil(date(2026, 9, 16), cal)  # suspensión
    assert not es_habil(date(2026, 10, 1), cal)  # día cerrado
    assert es_habil(date(2026, 10, 2), cal)
    # viernes + 3 hábiles salta fin de semana y festivo: martes 13, miércoles 14, jueves 15
    assert calc_venc(date(2026, 10, 9), 3, True, cal) == date(2026, 10, 15)
    assert calc_venc(date(2026, 10, 9), 3, False, cal) == date(2026, 10, 12)
    assert calc_venc(None, 3, True, cal) is None
    assert calc_venc(date(2026, 10, 9), None, True, cal) is None


def test_reabierto_solo_levanta_festivos():
    festivo, sabado = date(2026, 10, 12), date(2026, 10, 10)
    cal = Calendario(festivos=frozenset({festivo}), reabiertos=frozenset({festivo, sabado}))
    assert es_habil(festivo, cal)
    assert not es_habil(sabado, cal)
