import json
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.server.db.conversion import actuacion_desde_legacy, proceso_desde_legacy, stat_evento_desde_legacy
from app.server.db.models import Actuacion, Proceso, StatEvento, nuevo_id
from app.server.db.seeds import SEED_DIR
from app.server.services.sierju import completar_tipos_sierju


def vaciar(s: Session) -> None:
    """Borra procesos, actuaciones y datos estadísticos manuales; la configuración y el personal se conservan."""
    s.execute(delete(StatEvento))
    s.execute(delete(Actuacion))
    s.execute(delete(Proceso))


def cargar_ejemplos(s: Session, hoy: date | None = None) -> int:
    """Reemplaza procesos, actuaciones y datos estadísticos por los de ejemplo, con fechas relativas a hoy."""
    hoy = hoy or date.today()
    datos = json.loads((SEED_DIR / "ejemplos.json").read_text(encoding="utf-8"))

    def resolver(v):
        """Convierte "@-40" en una fecha relativa a hoy, también dentro de listas y objetos anidados."""
        if isinstance(v, str):
            return (hoy + timedelta(days=int(v[1:]))).isoformat() if v.startswith("@") else v
        if isinstance(v, dict):
            return {k: resolver(x) for k, x in v.items()}
        if isinstance(v, list):
            return [resolver(x) for x in v]
        return v

    vaciar(s)
    ids = {p["id"]: nuevo_id() for p in datos["procesos"]}
    for p in datos["procesos"]:
        s.add(proceso_desde_legacy({**resolver(p), "id": ids[p["id"]]}))
    s.flush()
    for a in datos["actuaciones"]:
        s.add(actuacion_desde_legacy({**resolver(a), "id": nuevo_id(), "procesoId": ids[a["procesoId"]]}))
    # los datos especiales no nacen de una actuación, así que también van de ejemplo
    for e in datos.get("statEventos", []):
        pid = ids.get(e.get("procesoId")) if e.get("procesoId") else None
        s.add(stat_evento_desde_legacy({**resolver(e), "id": nuevo_id(), "procesoId": pid}))
    completar_tipos_sierju(s)
    return len(datos["procesos"])
