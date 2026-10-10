"""Los datos que alimentan el formato SIERJU, derivados de procesos y actuaciones (puerto de la v2).

No se guardan: se calculan cada vez sobre el periodo pedido. Solo los registros manuales viven en la base
(`stat_eventos`), porque no nacen de ninguna actuación.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.server.domain import naturaleza as N
from app.server.domain.sierju import clasificar as C
from app.server.domain.sierju.secciones import SECCIONES, buscar_columna, buscar_fila

AUTOMATICO = "Automático"
MANUAL = "Manual"


@dataclass(frozen=True)
class Evento:
    fecha: date
    seccion: str
    fila: str
    columna: str
    cantidad: int = 1
    origen: str = AUTOMATICO
    proceso_id: str = ""
    nota: str = ""


@dataclass(frozen=True)
class Aviso:
    """Un dato que debía contarse pero no se pudo clasificar: se reporta en vez de perderlo en silencio."""

    fecha: date | None
    seccion: str
    proceso_id: str
    nota: str


@dataclass(frozen=True)
class Paquete:
    eventos: tuple[Evento, ...]
    avisos: tuple[Aviso, ...]
    automaticos: int
    manuales: int


def _en(f: date | None, desde: date, hasta: date) -> bool:
    return bool(f) and desde <= f <= hasta


class _Acumulador:
    def __init__(self) -> None:
        self.eventos: list[Evento] = []
        self.avisos: list[Aviso] = []

    def add(self, fecha, seccion, fila, columna, origen, proceso_id, nota="", cantidad=1) -> None:
        """Como el `add` de la v2: lo que queda incompleto se vuelve aviso, no evento."""
        if fecha and seccion and fila and columna:
            self.eventos.append(Evento(fecha, seccion, fila, columna, cantidad, origen, proceso_id, nota))
        else:
            self.avisos.append(Aviso(fecha, seccion, proceso_id, nota))

    def aviso(self, fecha, seccion, proceso_id, nota) -> None:
        self.avisos.append(Aviso(fecha, seccion, proceso_id, nota))


def _movimiento_proceso(ac: _Acumulador, p, desde: date, hasta: date) -> None:
    code = C.seccion_de_proceso(p)
    if code not in SECCIONES:
        return
    fila = C.fila_de_proceso(code, p)
    garantias = N.es_garantias(p.naturaleza)
    sols = list(p.solicitudes_penales) if garantias else []

    if garantias and sols:
        # en garantías cada solicitud entra y sale por separado, sin duplicar el proceso
        for s in sols:
            f = s.fecha or p.fecha_rad
            if _en(f, desde, hasta):
                col = C.columna_entrada_solicitud(code, s)
                if col and fila:
                    ac.add(f, code, fila, col, "Solicitud control de garantías", p.id, s.tipo or "Solicitud penal")
                else:
                    ac.aviso(f, code, p.id, f"No se pudo clasificar solicitud penal: {s.tipo or ''}")
            if s.salida and _en(s.fecha_salida, desde, hasta):
                col = buscar_columna(code, s.salida)
                nota = (s.tipo or "Solicitud penal") + (f" · {s.detalle_salida}" if s.detalle_salida else "")
                if col and fila:
                    ac.add(s.fecha_salida, code, fila, col, "Salida solicitud control de garantías", p.id, nota)
                else:
                    ac.aviso(s.fecha_salida, code, p.id, f"No se pudo clasificar salida de solicitud penal: {s.salida}")
    elif _en(p.fecha_rad, desde, hasta):
        col = C.columna_entrada(code, p)
        if col and fila:
            ac.add(p.fecha_rad, code, fila, col, "Proceso/solicitud", p.id, "Entrada automática")
        else:
            ac.aviso(p.fecha_rad, code, p.id, f"No se pudo clasificar entrada: {p.tipo_entrada or ''}")

    if not garantias and p.forma_salida and _en(p.fecha_terminacion, desde, hasta):
        col = C.columna_salida(code, p)
        if col and fila:
            ac.add(p.fecha_terminacion, code, fila, col, "Proceso/solicitud", p.id, "Salida automática")
        else:
            ac.aviso(p.fecha_terminacion, code, p.id, f"No se pudo clasificar salida: {p.forma_salida}")

    if _en(p.fecha_archivo, desde, hasta) and (s := SECCIONES.get(C.SEC_ARCHIVO)):
        ac.add(p.fecha_archivo, C.SEC_ARCHIVO, s.filas[0], s.columnas[0], "Archivo", p.id, "Archivo definitivo")


def _movimiento_actuacion(ac: _Acumulador, a, p, desde: date, hasta: date) -> None:
    if a.tipo_providencia and _en(a.providencia, desde, hasta):
        fila = C.fila_providencia(a.tipo_providencia)
        col = C.columna_providencia(p)
        if fila and col:
            ac.add(a.providencia, C.SEC_PROVIDENCIAS, fila, col, "Providencia", p.id, a.descripcion)
        else:
            ac.aviso(a.providencia, C.SEC_PROVIDENCIAS, p.id, "Providencia sin clasificación completa")

    if a.es_audiencia and _en(a.aud_fecha, desde, hasta) and (code := C.seccion_audiencia(p)):
        fila = C.fila_audiencia(code, p, a)
        # toda audiencia cuenta como programada; si ya tiene resultado, se registra además
        col_prog = C.columna_audiencia_programada(code, p, a)
        inmediata = N.es_penal(p.naturaleza) and a.aud_inmediata
        if fila and col_prog:
            origen = "Audiencia inmediata" if inmediata else "Audiencia programada"
            ac.add(a.aud_fecha, code, fila, col_prog, origen, p.id, a.descripcion)
        estado = a.aud_estado or "Programada"
        if estado != "Programada":
            col = C.columna_audiencia(code, a)
            if fila and col:
                ac.add(a.aud_fecha, code, fila, col, "Resultado audiencia", p.id, a.descripcion)
            else:
                ac.aviso(a.aud_fecha, code, p.id, "Resultado de audiencia sin clasificación completa")
            if a.aud_causa and ("Aplaz" in estado or "Cancel" in estado):
                cc = C.columna_causa_audiencia(code, p, a)
                if fila and cc:
                    ac.add(a.aud_fecha, code, fila, cc, "Causa audiencia", p.id, a.aud_causa)

    if a.recurso_tipo and _en(a.recurso_fecha, desde, hasta):
        fila = buscar_fila(C.SEC_RECURSOS, a.recurso_tipo)
        col = C.columna_recurso(C.SEC_RECURSOS, p, a)
        if fila and col:
            ac.add(a.recurso_fecha, C.SEC_RECURSOS, fila, col, "Recurso", p.id, a.descripcion)
        else:
            ac.aviso(a.recurso_fecha, C.SEC_RECURSOS, p.id, "Recurso interpuesto sin clasificación completa")

    if a.superior_resultado and _en(a.superior_fecha, desde, hasta):
        fila = buscar_fila(C.SEC_RECURSOS_DECIDIDOS, a.superior_resultado)
        col = C.columna_recurso(C.SEC_RECURSOS_DECIDIDOS, p, a)
        if fila and col:
            ac.add(a.superior_fecha, C.SEC_RECURSOS_DECIDIDOS, fila, col, "Decisión superior", p.id, a.descripcion)
        else:
            ac.aviso(a.superior_fecha, C.SEC_RECURSOS_DECIDIDOS, p.id, "Decisión del superior sin clasificación completa")

    esp = SECCIONES.get(C.SEC_ESPECIALES)
    if esp and a.remate_realizado and _en(a.aud_fecha, desde, hasta):
        ac.add(a.aud_fecha, C.SEC_ESPECIALES, buscar_fila(C.SEC_ESPECIALES, "DILIGENCIAS DE REMATE"), esp.columnas[0],
               "Actuación especial", p.id, a.descripcion)  # fmt: skip
    if esp and a.amparo_pobreza_concedido and _en(a.providencia, desde, hasta):
        ac.add(a.providencia, C.SEC_ESPECIALES, buscar_fila(C.SEC_ESPECIALES, "AMPAROS DE POBREZA"), esp.columnas[0],
               "Actuación especial", p.id, a.descripcion)  # fmt: skip

    # lo que se mueve después de terminado el proceso alimenta la sección de trámite posterior
    if not a.tp_tipo and p.fecha_terminacion:
        consulta = a.tipo_solicitud or a.materia or "OTROS"
        if a.fecha_memorial and a.fecha_memorial > p.fecha_terminacion and _en(a.fecha_memorial, desde, hasta):
            fila = buscar_fila(C.SEC_TP_ACTUACION, consulta)
            col = buscar_columna(C.SEC_TP_ACTUACION, "NÚMERO DE SOLICITUDES QUE INICIAN DURANTE EL PERIODO")
            if fila and col:
                ac.add(a.fecha_memorial, C.SEC_TP_ACTUACION, fila, col, "Trámite posterior", p.id, a.descripcion)
        if a.providencia and a.providencia > p.fecha_terminacion and _en(a.providencia, desde, hasta):
            fila = buscar_fila(C.SEC_TP_ACTUACION, consulta)
            col = buscar_columna(C.SEC_TP_ACTUACION, "TERMINAN TRÁMITE POSTERIOR")
            if fila and col:
                ac.add(a.providencia, C.SEC_TP_ACTUACION, fila, col, "Trámite posterior", p.id, a.descripcion)


def _inventario(ac: _Acumulador, procesos: Iterable, desde: date, hasta: date) -> None:
    """Lo que estaba abierto al abrir y al cerrar el periodo. En garantías no hay inventario de procesos."""
    for p in procesos:
        if N.es_garantias(p.naturaleza):
            continue
        code = C.seccion_de_proceso(p)
        if code not in SECCIONES:
            continue
        fila = C.fila_de_proceso(code, p)
        if not fila:
            continue
        cierre = p.fecha_terminacion or p.fecha_archivo
        existia_antes = (not p.fecha_rad) or p.fecha_rad < desde
        if existia_antes and not (cierre and cierre < desde):
            if col := C.columna_inventario(code, C.INICIAR):
                ac.add(desde, code, fila, col, "Inventario inicial", p.id, "Stock al iniciar")
        existia_hasta = (not p.fecha_rad) or p.fecha_rad <= hasta
        if existia_hasta and not (cierre and cierre <= hasta):
            if col := C.columna_inventario(code, C.FINAL):
                ac.add(hasta, code, fila, col, "Inventario final", p.id, "Stock al finalizar")


def _tutela_extras(ac: _Acumulador, procesos: Iterable, desde: date, hasta: date) -> None:
    """Derecho tutelado cuando se concede, y la medida provisional como providencia."""
    for p in procesos:
        if p.naturaleza != "Tutela":
            continue
        derecho = p.tipo_sierju or p.clase or ""
        if p.forma_salida == "Concede" and _en(p.fecha_terminacion, desde, hasta):
            fila = buscar_fila(C.SEC_TUTELAS, derecho) or buscar_fila(C.SEC_TUTELAS, "OTROS")
            col = buscar_columna(C.SEC_TUTELAS, "DERECHOS FUNDAMENTALES TUTELADOS")
            if fila and col:
                ac.add(p.fecha_terminacion, C.SEC_TUTELAS, fila, col, "Derecho tutelado", p.id)
        if p.medida_tutela == "Sí" and _en(p.fecha_rad, desde, hasta):
            fila = buscar_fila(C.SEC_PROVIDENCIAS, "MEDIDAS CAUTELARES")
            col = buscar_columna(C.SEC_PROVIDENCIAS, "TUTELAS")
            if fila and col:
                ac.add(p.fecha_rad, C.SEC_PROVIDENCIAS, fila, col, "Medida provisional tutela", p.id)


def _tramite_posterior(ac: _Acumulador, procesos: Iterable, actuaciones: Iterable, desde: date, hasta: date) -> None:
    if C.SEC_TP_PROCESO in SECCIONES:
        for p in procesos:
            if not p.tramite_posterior or p.naturaleza not in ("Civil", "Familia"):
                continue
            fila = buscar_fila(C.SEC_TP_PROCESO, "CIVILES" if p.naturaleza == "Civil" else "FAMILIA")
            if not fila:
                continue
            ini, fin = p.fecha_tramite_posterior, p.fecha_archivo
            if _en(ini, desde, hasta) and (c := buscar_columna(C.SEC_TP_PROCESO, "INICIAN")):
                ac.add(ini, C.SEC_TP_PROCESO, fila, c, "Trámite posterior inicia", p.id)
            if _en(fin, desde, hasta) and (c := buscar_columna(C.SEC_TP_PROCESO, "TERMINAN")):
                ac.add(fin, C.SEC_TP_PROCESO, fila, c, "Trámite posterior termina", p.id)
            if ini and ini < desde and not (fin and fin < desde):
                if c := buscar_columna(C.SEC_TP_PROCESO, "INVENTARIO AL INICIAR EL PERIODO-CON TRÁMITE"):
                    ac.add(desde, C.SEC_TP_PROCESO, fila, c, "TP inv inicial", p.id)
            if ini and ini <= hasta and not (fin and fin <= hasta):
                if c := buscar_columna(C.SEC_TP_PROCESO, "INVENTARIO AL FINAL DEL PERIODO-CON TRÁMITE"):
                    ac.add(hasta, C.SEC_TP_PROCESO, fila, c, "TP inv final", p.id)

    if C.SEC_TP_ACTUACION in SECCIONES:
        for a in actuaciones:
            if not a.tp_tipo:
                continue
            fila = buscar_fila(C.SEC_TP_ACTUACION, a.tp_tipo)
            if not fila:
                continue
            ini = a.fecha_memorial or a.constancia
            fin = a.providencia or a.cumplida
            if _en(ini, desde, hasta) and (c := buscar_columna(C.SEC_TP_ACTUACION, "INICIAN")):
                ac.add(ini, C.SEC_TP_ACTUACION, fila, c, "TP actuación inicia", a.proceso_id, a.tp_tipo)
            if _en(fin, desde, hasta) and (c := buscar_columna(C.SEC_TP_ACTUACION, "TERMINAN")):
                ac.add(fin, C.SEC_TP_ACTUACION, fila, c, "TP actuación termina", a.proceso_id, a.tp_tipo)
            if ini and ini < desde and not (fin and fin < desde):
                if c := buscar_columna(C.SEC_TP_ACTUACION, "INVENTARIO AL INICIAR EL PERIODO"):
                    ac.add(desde, C.SEC_TP_ACTUACION, fila, c, "TP act inv inicial", a.proceso_id)
            if ini and ini <= hasta and not (fin and fin <= hasta):
                if c := buscar_columna(C.SEC_TP_ACTUACION, "INVENTARIO AL FINALIZAR EL PERIODO"):
                    ac.add(hasta, C.SEC_TP_ACTUACION, fila, c, "TP act inv final", a.proceso_id)


def manual_a_evento(e) -> Evento:
    return Evento(e.fecha, e.seccion, e.fila, e.columna, e.cantidad or 1, MANUAL, e.proceso_id or "", e.nota or "")


def todos(procesos, actuaciones, manuales, desde: date, hasta: date) -> Paquete:
    """Todo lo que cuenta en el periodo, en el mismo orden que la v2: procesos, actuaciones y luego los agregados."""
    procesos = list(procesos)
    actuaciones = list(actuaciones)
    por_id = {p.id: p for p in procesos}

    ac = _Acumulador()
    for p in procesos:
        _movimiento_proceso(ac, p, desde, hasta)
    for a in actuaciones:
        if p := por_id.get(a.proceso_id):
            _movimiento_actuacion(ac, a, p, desde, hasta)
    automaticos = list(ac.eventos)
    avisos = list(ac.avisos)

    agregados = _Acumulador()
    _inventario(agregados, procesos, desde, hasta)
    _tramite_posterior(agregados, procesos, actuaciones, desde, hasta)
    _tutela_extras(agregados, procesos, desde, hasta)

    de_mano = [manual_a_evento(e) for e in manuales if _en(e.fecha, desde, hasta)]
    eventos = automaticos + agregados.eventos + de_mano
    return Paquete(
        eventos=tuple(eventos),
        avisos=tuple(avisos),
        automaticos=len(automaticos) + len(agregados.eventos),
        manuales=len(de_mano),
    )
