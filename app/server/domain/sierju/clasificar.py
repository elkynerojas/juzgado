"""A qué sección, fila y columna del formato SIERJU corresponde cada dato (puerto de la v2 del HTML)."""

from app.server.db.seeds import cargar_sierju
from app.server.domain import naturaleza as N
from app.server.domain.sierju.secciones import SECCIONES, buscar_columna, buscar_fila, columna_por_codigo
from app.server.domain.sierju.texto import norm

# secciones a las que se mandan datos que no dependen de la naturaleza
SEC_ARCHIVO = "SEC3746"
SEC_PROVIDENCIAS = "SEC4416"
SEC_AUD_CIVIL = "SEC4603"
SEC_AUD_PENAL = "SEC5414"
SEC_RECURSOS = "SEC5082"
SEC_RECURSOS_DECIDIDOS = "SEC5083"
SEC_ESPECIALES = "SEC5086"
SEC_TUTELAS = "SEC5880"
SEC_TP_PROCESO = "SEC5209"
SEC_TP_ACTUACION = "SEC4777"

# naturaleza -> sección de movimiento. Se conservan las que la aplicación no genera pero llegan en respaldos.
_SECCION_POR_NATURALEZA = {
    "Penal Ley 600 - Conocimiento": "SEC5957",
    "Penal 906 - Garantías": "SEC5959",
    "Penal 1098 - Garantías": "SEC5970",
    "Penal 1826 - Garantías adolescentes": "SEC5956",
    "Penal 1826 - Garantías adultos": "SEC5955",
    "Penal 1826 - Garantías": "SEC5955",
    "Penal 906 - Conocimiento": "SEC5958",
    "Penal 1826 - Conocimiento adultos": "SEC5964",
    "Penal 1826 - Conocimiento": "SEC5964",
    "Incidente reparación integral Ley 906": "SEC5175",
    "Penal 906 - Incidente reparación integral": "SEC5175",
    "Incidente reparación integral Ley 1826": "SEC5177",
    "Penal 1826 - Incidente reparación integral": "SEC5177",
    "Civil": "SEC4587",
    "Familia": "SEC5211",
    "Hábeas corpus": "SEC4826",
    "Tutela": "SEC5880",
    "Incidente de desacato": "SEC5902",
    "Desacato": "SEC5902",
    "Ejecución de penas - segunda instancia": "SEC5232",
    "Penal - Ejecución de penas segunda instancia": "SEC5232",
    "Solicitudes Ley 1820": "SEC5071",
    "Penal - Solicitudes Ley 1820": "SEC5071",
    "Otro": "SEC4415",
}


def seccion_de_proceso(p) -> str:
    return _SECCION_POR_NATURALEZA.get(p.naturaleza or "", "")


def fila_de_proceso(code: str, p) -> str:
    return buscar_fila(code, p.clase or p.tipo_sierju or "") or buscar_fila(code, p.tipo_sierju or "") or buscar_fila(code, "OTROS")


# ---------- entradas y salidas ----------


def columna_entrada(code: str, p) -> str:
    return buscar_columna(code, p.tipo_entrada or "Por reparto")


def columna_entrada_solicitud(code: str, s) -> str:
    """Una solicitud de garantías entra por su tipo si es nueva, o por su forma de reingreso."""
    if not s:
        return ""
    entrada = s.entrada or "Nueva solicitud"
    return buscar_columna(code, s.tipo or "" if entrada == "Nueva solicitud" else entrada)


def columna_salida(code: str, p) -> str:
    return buscar_columna(code, p.forma_salida or "")


# ---------- providencias ----------

_PROVIDENCIA_FILA = {
    "Auto interlocutorio": "AUTOS INTERLOCUTORIOS",
    "Sentencia": "SENTENCIAS",
    "Medida cautelar": "MEDIDAS CAUTELARES",
}


def fila_providencia(tipo: str) -> str:
    return buscar_fila(SEC_PROVIDENCIAS, _PROVIDENCIA_FILA.get(tipo, tipo))


def columna_providencia(p) -> str:
    n = p.naturaleza or ""
    escrito = p.via == "Escrito"
    if n == "Civil":
        q = ("ESCRITO CIVIL" if escrito else "ORAL CIVIL") + " 1 INSTANCIA"
    elif n == "Familia":
        q = ("ESCRITO FAMILIA" if escrito else "ORAL FAMILIA") + " UNICA INSTANCIA"
    elif n == "Penal 906 - Garantías":
        q = "CONTROL DE GARANTÍAS LEY 906"
    elif n == "Penal 906 - Conocimiento":
        q = "CONOCIMIENTO"
    elif n == "Penal 1098 - Garantías":
        q = "CONTROL DE GARANTÍAS LEY 1098"
    elif "1826" in n and "Garantías adolescentes" in n:
        q = "GARANTÍAS ADOLESCENTES LEY 1826"
    elif "1826" in n and "Garantías" in n:
        q = "GARANTÍAS ADULTOS LEY 1826"
    elif "1826" in n and "Conocimiento" in n:
        q = "CONOCIMIENTO MUNICIPAL"
    elif n == "Tutela":
        q = "TUTELAS"
    elif "desacato" in n:
        q = "INCIDENTES DE DESACATO"
    elif n == "Hábeas corpus":
        q = "HABEAS CORPUS"
    elif "Ley 600" in n:
        q = "LEY 600 DE 2000"
    else:
        return ""
    return buscar_columna(SEC_PROVIDENCIAS, q)


# ---------- audiencias ----------

_AUD_COLUMNA = {
    "Realizada": "AUDIENCIAS REALIZADAS",
    "Suspendida": "AUDIENCIAS SUSPENDIDAS",
    "Aplazada": "AUDIENCIAS APLAZADAS",
    "Cancelada / no realizada": "AUDIENCIAS CANCELADAS O NO REALIZADAS",
    "Programada": "AUDIENCIAS PROGRAMADAS",
}


def seccion_audiencia(p) -> str:
    if p.naturaleza in ("Civil", "Familia"):
        return SEC_AUD_CIVIL
    return SEC_AUD_PENAL if N.es_penal(p.naturaleza) else ""


def fila_audiencia(code: str, p, a) -> str:
    if code == SEC_AUD_CIVIL:
        return buscar_fila(code, "FAMILIA" if p.naturaleza == "Familia" else "CIVIL")
    return buscar_fila(code, a.aud_tipo or p.naturaleza or "OTRAS AUDIENCIAS") or buscar_fila(code, "OTRAS")


def columna_audiencia(code: str, a) -> str:
    estado = a.aud_estado or "Programada"
    return buscar_columna(code, _AUD_COLUMNA.get(estado, estado))


def columna_audiencia_programada(code: str, p, a) -> str:
    """Las audiencias penales sin programación previa van a su propia columna."""
    inmediata = N.es_penal(p.naturaleza) and a.aud_inmediata
    return buscar_columna(code, "AUDIENCIAS INMEDIATAS" if inmediata else "AUDIENCIAS PROGRAMADAS")


def columna_causa_audiencia(code: str, p, a) -> str:
    """La causa se ubica por el código de columna, no por su texto: la de COL6828 trae un salto de línea."""
    estado = a.aud_estado or ""
    if "Aplaz" not in estado and "Cancel" not in estado:
        return ""
    rama = "penal" if N.es_penal(p.naturaleza) else "civil"
    clave = f"{rama}_{'cancelada' if 'Cancel' in estado else 'aplazada'}"
    codigo = cargar_sierju()["audiencias"]["columnas_causa"][clave].get(a.aud_causa or "")
    return columna_por_codigo(code, codigo) if codigo else ""


# ---------- recursos ----------


def columna_recurso(code: str, p, a) -> str:
    n = p.naturaleza or ""
    objeto = a.recurso_objeto or a.tipo_providencia or "Auto"
    sentencia = "SENT" in norm(objeto)
    escrito = p.via == "Escrito"
    if n == "Civil":
        q = ("ESCRITO CIVIL" if escrito else "ORAL CIVIL") + " 1 INSTANCIA " + ("SENTENCIAS" if sentencia else "AUTOS")
    elif n == "Familia":
        # la v2 consulta "ORAL CIVIL" también en familia; se conserva para no mover los conteos
        q = ("ESCRITO CIVIL" if escrito else "ORAL CIVIL") + " " + ("SENTENCIAS" if sentencia else "AUTOS")
    elif n == "Tutela":
        q = "TUTELAS"
    elif "desacato" in n:
        q = "INCIDENTES DE DESACATO"
    elif n == "Hábeas corpus":
        q = "HABEAS CORPUS"
    elif n == "Penal 906 - Garantías":
        q = "ORAL AUTOS GARANTÍAS"
    elif n == "Penal 906 - Conocimiento":
        q = "ORAL SENTENCIAS" if sentencia else "ORAL AUTOS CONOCIMIENTO"
    elif n == "Penal 1098 - Garantías":
        q = "ORAL AUTOS"
    elif "1826" in n and "Garantías adolescentes" in n:
        q = "LEY 1826 AUTOS GARANTÍAS ADOLESCENTES"
    elif "1826" in n and "Garantías" in n:
        q = "LEY 1826 AUTOS GARANTÍAS ADULTOS"
    elif "1826" in n and "Conocimiento" in n:
        q = "LEY 1826 SENTENCIAS ADULTOS" if sentencia else "LEY 1826 AUTOS CONOCIMIENTO ADULTOS"
    elif "Ley 600" in n:
        q = "ESCRITURAL SENTENCIAS" if sentencia else "ESCRITURAL AUTOS"
    else:
        q = ""
    return buscar_columna(code, q)


# ---------- inventario ----------

INICIAR = "INICIAR"
FINAL = "FINAL"

_INV_PREFERIDAS = {
    INICIAR: (
        "INVENTARIO AL INICIAR EL PERIODO CON TRAMITE",
        "INVENTARIO AL INICIAR EL PERIODO",
        "INVENTARIO DE TUTELAS AL INICIAR EL PERIODO",
        "INVENTARIO INCIDENTES DE DESACATO AL INICIAR EL PERIODO",
        "INVENTARIO DE PROCESOS SIN SENTENCIA O DECISION QUE PONGA FIN A LA INSTANCIA",
    ),
    FINAL: (
        "INVENTARIO AL FINAL DEL PERIODO CON TRAMITE",
        "INVENTARIO AL FINALIZAR EL PERIODO",
        "INVENTARIO DE TUTELAS AL FINALIZAR EL PERIODO",
        "INVENTARIO INCIDENTES DE DESACATO AL FINALIZAR EL PERIODO",
    ),
}
# el formato tiene columnas de conteo físico y de diferencia que no son inventario del sistema
_INV_EXCLUIDAS = ("FISICO", "DIFERENCIA")


def columna_inventario(code: str, fase: str) -> str:
    from app.server.domain.sierju.texto import mejor

    s = SECCIONES.get(code)
    if not s:
        return ""
    for q in _INV_PREFERIDAS[fase]:
        c = mejor(s.columnas, q)
        if c and not any(x in norm(c) for x in _INV_EXCLUIDAS):
            return c
    for c in s.columnas:
        nx = norm(c)
        if fase in nx and not any(x in nx for x in _INV_EXCLUIDAS) and "SIN TRAMITE" not in nx:
            return c
    return ""
