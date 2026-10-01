import json
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy
from app.server.db.models import Actuacion, Proceso, nuevo_id
from app.server.db.seeds import SEED_DIR


def vaciar(s: Session) -> None:
    s.execute(delete(Actuacion))
    s.execute(delete(Proceso))


def cargar_ejemplos(s: Session, hoy: date | None = None) -> int:
    """Reemplaza procesos y actuaciones por los de ejemplo, con fechas relativas a hoy."""
    hoy = hoy or date.today()
    datos = json.loads((SEED_DIR / "ejemplos.json").read_text(encoding="utf-8"))

    def resolver(d: dict) -> dict:
        return {
            k: (hoy + timedelta(days=int(v[1:]))).isoformat() if isinstance(v, str) and v.startswith("@") else v
            for k, v in d.items()
        }

    vaciar(s)
    ids = {p["id"]: nuevo_id() for p in datos["procesos"]}
    for p in datos["procesos"]:
        s.add(proceso_desde_legacy({**p, "id": ids[p["id"]]}))
    s.flush()
    for a in datos["actuaciones"]:
        s.add(actuacion_desde_legacy({**resolver(a), "id": nuevo_id(), "procesoId": ids[a["procesoId"]]}))
    return len(datos["procesos"])
