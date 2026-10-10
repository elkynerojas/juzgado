"""Naturalezas del proceso y las listas SIERJU que dependen de ella (v2 del HTML)."""

import unicodedata

from app.server.db.seeds import cargar_sierju

CIVIL = "Civil"
FAMILIA = "Familia"
PENAL = "Penal"
TUTELA = "Tutela"
DESACATO = "Incidente de desacato"
DESACATO_CORTO = "Desacato"
HABEAS = "Hábeas corpus"
OTRO = "Otro"
GARANTIAS = "Garantías"
CONOCIMIENTO = "Conocimiento"
LEYES_PENALES = ("906", "1826")

# lo que se elige en el formulario; la penal se guarda compuesta con componer_naturaleza()
NATURALEZAS = (CIVIL, FAMILIA, PENAL, TUTELA, DESACATO, HABEAS, OTRO)

AREA_CIVIL = "Civil"
AREA_FAMILIA = "Familia"
AREA_PENAL = "Penal"
AREA_CONSTITUCIONAL = "Constitucional"
AREA_OTROS = "Otros"
AREAS = (AREA_CIVIL, AREA_FAMILIA, AREA_PENAL, AREA_CONSTITUCIONAL, AREA_OTROS)

_GESTION_PENAL = (
    "Recurso de reposición",
    "Recurso de apelación",
    "Solicitud de aplazamiento de audiencia",
    "Oficio",
    "Respuesta entidad",
    "Otro",
)
_GESTION_TUTELA = (
    "Acción de tutela",
    "Medida provisional",
    "Respuesta entidad",
    "Impugnación",
    "Incidente de desacato",
    "Requerimiento de cumplimiento",
    "Oficio",
    "Otro",
)
_GESTION_DESACATO = (
    "Solicitud de incidente de desacato",
    "Requerimiento previo",
    "Apertura de incidente",
    "Pruebas",
    "Decisión de desacato",
    "Consulta",
    "Otro",
)
_ENTRADAS_DESACATO = (
    "Ingreso de incidentes de desacato durante el periodo",
    "Reingreso por nulidad incidentes de desacato",
    "Otras entradas no efectivas",
)
# la única salida que exige explicar el motivo
SALIDA_NO_EFECTIVA = "Otras salidas no efectivas"
_SALIDAS_GARANTIAS_ACT = ("Remitidos a otros despachos", "Autos decisiones de fondo", SALIDA_NO_EFECTIVA)


def _sj() -> dict:
    return cargar_sierju()


def es_penal(nat: str | None) -> bool:
    return isinstance(nat, str) and nat.startswith(PENAL)


def es_garantias(nat: str | None) -> bool:
    return es_penal(nat) and GARANTIAS in nat


def es_conocimiento(nat: str | None) -> bool:
    return es_penal(nat) and CONOCIMIENTO in nat


def es_desacato(nat: str | None) -> bool:
    return nat in (DESACATO, DESACATO_CORTO)


def es_constitucional(nat: str | None) -> bool:
    return nat in (TUTELA, DESACATO, DESACATO_CORTO, HABEAS)


def componer_naturaleza(ley: str, procedimiento: str) -> str:
    if ley not in LEYES_PENALES or procedimiento not in (GARANTIAS, CONOCIMIENTO):
        raise ValueError(f"Naturaleza penal inválida: ley {ley!r}, {procedimiento!r}")
    return f"{PENAL} {ley} - {procedimiento}"


PENALES = tuple(componer_naturaleza(ley, p) for ley in LEYES_PENALES for p in (GARANTIAS, CONOCIMIENTO))

# lo que la aplicación guarda: las simples (sin "Penal" a secas) y las penales ya compuestas
NATURALEZAS_GUARDABLES = (CIVIL, FAMILIA, TUTELA, DESACATO, HABEAS, OTRO, *PENALES)


def guardable(nat: str | None) -> bool:
    """Acepta lo que el formulario produce. "Penal" a secas no, porque le falta ley y procedimiento.

    Tolera otras penales compuestas ("Penal Ley 600 - Conocimiento", "Penal 1098 - Garantías") y el alias
    "Desacato": no las genera la aplicación, pero llegan en respaldos del HTML y hay que poder editarlas.
    """
    if nat in NATURALEZAS_GUARDABLES or nat == DESACATO_CORTO:
        return True
    return es_penal(nat) and " - " in nat


def area_de(nat: str | None) -> str:
    """Área de trabajo a la que pertenece el proceso; agrupa los filtros de Procesos y de Audiencias."""
    if nat == CIVIL:
        return AREA_CIVIL
    if nat == FAMILIA:
        return AREA_FAMILIA
    if es_penal(nat):
        return AREA_PENAL
    if es_constitucional(nat):
        return AREA_CONSTITUCIONAL
    return AREA_OTROS


def _ley(nat: str) -> str:
    return "1826" if " 1826 " in f"{nat} " else "906"


def lista_sierju(nat: str | None) -> list[str]:
    """Tipos de proceso SIERJU, delitos o derechos invocados, según la naturaleza."""
    sj = _sj()
    if nat == FAMILIA:
        return sj["tipos"]["familia"]
    if es_penal(nat):
        clave = "garantias" if es_garantias(nat) else "conocimiento"
        return sj["delitos"][f"{clave}_{_ley(nat)}"]
    if nat == TUTELA or es_desacato(nat):
        return sj["tipos"]["derechos"]
    if nat == HABEAS:
        return sj["tipos"]["habeas"]
    return sj["tipos"]["civil"]


def lista_salidas(nat: str | None) -> list[str]:
    s = _sj()["salidas"]
    if nat == TUTELA:
        return s["tutela"]
    if es_desacato(nat):
        return s["desacato"]
    if nat == HABEAS:
        return s["habeas"]
    if es_conocimiento(nat):
        return s["penal_conocimiento"]
    if es_penal(nat):
        return s["penal_garantias"]
    return s["civil"]


def penal_solicitudes(nat: str | None) -> list[str]:
    sj = _sj()
    if es_garantias(nat):
        return sj["solicitudes_garantias"][_ley(nat)]
    if es_conocimiento(nat):
        return sj["entradas"]["penal_conocimiento"]
    return []


def entradas_sierju(nat: str | None) -> list[str]:
    e = _sj()["entradas"]
    if nat == CIVIL:
        return e["civil"]
    if nat == FAMILIA:
        return e["familia"]
    if nat == TUTELA:
        return e["tutela"]
    if nat == HABEAS:
        return e["habeas"]
    if es_desacato(nat):
        return list(_ENTRADAS_DESACATO)
    if es_garantias(nat):
        return [*penal_solicitudes(nat), "Reingreso", "Otras entradas no efectivas"]
    if es_conocimiento(nat):
        return e["penal_conocimiento"]
    return ["Por reparto", "Otras entradas no efectivas"]


def tipos_gestion(nat: str | None, catalogo: list[str]) -> list[str]:
    """Opciones de "tipo de solicitud" de la actuación. Sin repetidos (la v2 los mostraba dos veces)."""
    if es_penal(nat):
        lista = [*penal_solicitudes(nat), *_GESTION_PENAL]
    elif nat == TUTELA:
        lista = [*_GESTION_TUTELA, *catalogo]
    elif es_desacato(nat):
        lista = [*_GESTION_DESACATO, *catalogo]
    else:
        lista = list(catalogo)
    return list(dict.fromkeys(lista))


def salidas_act(nat: str | None) -> list[str]:
    if es_garantias(nat):
        return ["", *_SALIDAS_GARANTIAS_ACT]
    return ["", *lista_salidas(nat)]


def _orden_alfabetico(texto: str) -> tuple:
    # aproxima localeCompare: sin tildes ni mayúsculas primero, y el texto exacto para desempatar
    base = unicodedata.normalize("NFD", texto)
    return ("".join(c for c in base if not unicodedata.combining(c)).casefold(), texto)


def delitos_unificados(procedimiento: str) -> list[tuple[str, str]]:
    """Delitos de las leyes 906 y 1826 para el procedimiento dado, como (delito, ley), en orden alfabético."""
    clave = "garantias" if procedimiento == GARANTIAS else "conocimiento"
    d = _sj()["delitos"]
    pares = dict.fromkeys([(x, "906") for x in d[f"{clave}_906"]] + [(x, "1826") for x in d[f"{clave}_1826"]])
    return sorted(pares, key=lambda p: _orden_alfabetico(p[0]))


_DERECHOS = (
    (("salud",), "Salud"),
    (("seguridad social", "pension", "pensión"), "Seguridad social"),
    (("vida",), "Vida"),
    (("mínimo vital", "minimo vital"), "Mínimo vital"),
    (("igualdad",), "Igualdad"),
    (("educaci",), "Educación"),
    (("debido proceso",), "Debido proceso"),
    (("petici",), "Derecho de petición"),
    (("informaci",), "Derecho a la información pública"),
    (("providencia",), "Contra providencias judiciales"),
    (("ambiente",), "Medio ambiente"),
)

_FAMILIA = (
    (lambda s: "aliment" in s, "Alimentos (fijación/aumento/disminución/exoneración)"),
    (lambda s: "divorcio" in s, "Divorcio de común acuerdo"),
    (lambda s: "restablecimiento" in s, "Restablecimiento de derechos NNA"),
    (lambda s: "permiso" in s and ("sal" in s or "pa" in s), "Permiso para salir del país"),
    (lambda s: "adopt" in s or "adopci" in s, "Declaratoria de adoptabilidad"),
    (lambda s: "homologaci" in s, "Homologaciones"),
    (lambda s: "violencia" in s or "protecci" in s, "Medidas de protección por violencia intrafamiliar"),
    (lambda s: "restitución internacional" in s or "restitucion internacional" in s, "Restitución internacional de NNA"),
    (lambda s: "custodia" in s or "visitas" in s, "Custodia"),
)

_VERBALES = (
    "reivindicat", "simulaci", "resoluci", "incumplimiento", "responsabilidad civil", "nulidad de escritura",
    "enriquecimiento", "restitución de inmueble", "restitucion de inmueble", "verbal",
)  # fmt: skip

_CIVIL = (
    (lambda s: "hipotec" in s, "Ejecutivos-Hipotecario"),
    (
        lambda s: "ejecutiv" in s or s in ("sgd", "sgde") or any(k in s for k in ("sumas de dinero", "garantía mobiliaria", "garantia mobiliaria")),
        "Ejecutivos",
    ),
    (lambda s: "pertenencia" in s, "Pertenencia"),
    (lambda s: "sucesi" in s, "Liquidación-Sucesión"),
    (lambda s: any(k in s for k in ("divisorio", "división y/o venta", "division y/o venta")), "Declarativos-Divisorios"),
    (lambda s: "deslinde" in s, "Deslinde y amojonamiento"),
    (lambda s: "servidumbre" in s, "Servidumbres"),
    (lambda s: "posesori" in s, "Posesorios"),
    (lambda s: "verbal sumario" in s or "verbal sumaria" in s, "Declarativos-Verbal sumario"),
    (lambda s: "monitorio" in s, "Declarativos-Otros"),
    (lambda s: any(k in s for k in _VERBALES), "Declarativos-Verbales"),
    (lambda s: any(k in s for k in ("prueba anticipada", "comisi", "exhorto")), "Otros procesos"),
    (lambda s: "avalúo" in s or "avaluo" in s, "Servidumbres"),
)


def _sug_penal(clase: str, nat: str) -> str:
    arr = lista_sierju(nat)
    pz = clase.lower()

    def f(kw: str) -> str:
        return next((x for x in arr if kw in x.lower()), "")

    r = ""
    if "aliment" in pz and "agrav" in pz:
        r = f("inasistencia alimentaria agravada") or f("234. inasistencia")
    elif "aliment" in pz:
        r = f("233. inasistencia") or f("inasistencia alimentaria")
    elif "intrafamiliar" in pz or "violencia" in pz:
        r = f("violencia intrafamiliar")
    elif "les" in pz and "culpos" in pz:
        r = f("lesiones culposas")
    elif "lesion" in pz:
        r = f("lesiones dolosas") or f("otros delitos de lesiones")
    elif "hurto" in pz and ("calif" in pz or "agrav" in pz):
        r = f("hurto agravado") or f("hurto calificado")
    elif "hurto" in pz:
        r = f("hurto")
    elif "daño" in pz or "dano" in pz:
        r = f("daño en bien")
    elif "injuria" in pz:
        r = f("injuria")
    elif "calumnia" in pz:
        r = f("calumnia")
    elif "estafa" in pz:
        r = f("estafa")
    elif "custodia" in pz:
        r = f("ejercicio arbitrario de la custodia")
    elif "homic" in pz and "culpos" in pz:
        r = f("homicidio culposo")
    elif "homic" in pz:
        r = f("103. homicidio") or f("homicidio")
    return r or f("otros") or (arr[0] if arr else "")


def sug_sierju(clase: str | None, nat: str | None) -> str:
    """Tipo SIERJU sugerido para la clase de proceso (o delito / derecho invocado) según la naturaleza."""
    clase = clase or ""
    if nat == HABEAS:
        return "Acción de hábeas corpus"
    # la v2 no trataba "Incidente de desacato" aquí y lo clasificaba como civil
    if nat == TUTELA or es_desacato(nat):
        t = clase.lower()
        return next((v for claves, v in _DERECHOS if any(k in t for k in claves)), "Otros")
    if es_penal(nat):
        return _sug_penal(clase, nat)
    if not clase:
        return ""
    mapa = _sj()["mapa_tipos"]
    if clase in mapa:
        return mapa[clase]
    s = clase.lower()
    reglas = _FAMILIA if nat == FAMILIA else _CIVIL
    return next((v for cumple, v in reglas if cumple(s)), "Otros procesos")
