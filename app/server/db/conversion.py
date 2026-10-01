"""Conversión entre el formato del HTML original (camelCase, fechas como texto) y los modelos."""

from datetime import date

from app.server.db.models import Actuacion, Proceso


def a_fecha(valor) -> date | None:
    return date.fromisoformat(valor) if valor else None


def proceso_desde_legacy(d: dict) -> Proceso:
    return Proceso(
        id=d["id"],
        radicado=d.get("radicado") or "",
        naturaleza=d.get("naturaleza") or "",
        clase=d.get("clase") or "",
        demandante=d.get("demandante") or "",
        demandado=d.get("demandado") or "",
        fecha_rad=a_fecha(d.get("fechaRad")),
        situacion=d.get("situacion") or "Activo",
        macroetapa=d.get("macroetapa") or "",
        notas=d.get("notas") or "",
    )


def actuacion_desde_legacy(d: dict) -> Actuacion:
    paso = d.get("pasoIdx")
    return Actuacion(
        id=d["id"],
        proceso_id=d["procesoId"],
        cuaderno=d.get("cuaderno") or "",
        materia=d.get("materia") or "",
        tipo_solicitud=d.get("tipoSolicitud") or "",
        origen=d.get("origen") or "",
        descripcion=d.get("descripcion") or "",
        fecha_memorial=a_fecha(d.get("fechaMemorial")),
        constancia=a_fecha(d.get("constancia")),
        pasa=d.get("pasa") or "",
        pase=a_fecha(d.get("pase")),
        providencia=a_fecha(d.get("providencia")),
        ejecutoria=a_fecha(d.get("ejecutoria")),
        cumplida=a_fecha(d.get("cumplida")),
        termino=d.get("termino") or "",
        termino_dias=d.get("terminoDias") or None,
        termino_habil=d.get("terminoHabil") is not False,
        fecha_inicio=a_fecha(d.get("fechaInicio")),
        suspende=bool(d.get("suspende")),
        obs=d.get("obs") or "",
        ruta_id=d.get("rutaId") or "",
        paso_idx=paso if isinstance(paso, int) else None,
    )
