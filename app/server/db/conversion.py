"""Conversión entre el formato del HTML original (camelCase, fechas como texto) y los modelos."""

from datetime import date

from app.server.db.models import Actuacion, Proceso, SolicitudPenal, StatEvento, nuevo_id


def a_fecha(valor) -> date | None:
    return date.fromisoformat(valor) if valor else None


def _texto(d: dict, clave: str, defecto: str = "") -> str:
    v = d.get(clave)
    return str(v) if v not in (None, "") else defecto


def _lista(v) -> list[str]:
    return [str(x) for x in v if x] if isinstance(v, list) else []


def solicitudes_desde_legacy(d: dict) -> list[SolicitudPenal]:
    lista = d.get("solicitudesPenales")
    if not isinstance(lista, list):
        # respaldos anteriores a la lista: una sola solicitud en `solicitudPenal` (como hace openProc de la v2)
        lista = []
        if d.get("solicitudPenal") and "Garantías" in (d.get("naturaleza") or ""):
            lista = [{"tipo": d["solicitudPenal"], "fecha": d.get("fechaRad")}]
    return [
        SolicitudPenal(
            id=_texto(r, "id") or nuevo_id(),
            orden=i,
            tipo=_texto(r, "tipo"),
            fecha=a_fecha(r.get("fecha")),
            entrada=_texto(r, "entrada", "Nueva solicitud"),
            salida=_texto(r, "salida"),
            fecha_salida=a_fecha(r.get("fechaSalida")),
            hora_salida=_texto(r, "horaSalida"),
            detalle_salida=_texto(r, "detalleSalida"),
        )
        for i, r in enumerate(x for x in lista if isinstance(x, dict))
    ]


def proceso_desde_legacy(d: dict) -> Proceso:
    p = Proceso(
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
        tipo_sierju=_texto(d, "tipoSierju"),
        via=_texto(d, "via", "Oral"),
        tipo_entrada=_texto(d, "tipoEntrada"),
        fecha_terminacion=a_fecha(d.get("fechaTerminacion")),
        fecha_archivo=a_fecha(d.get("fechaArchivo")),
        forma_salida=_texto(d, "formaSalida"),
        tramite_posterior=bool(d.get("tramitePosterior")),
        fecha_tramite_posterior=a_fecha(d.get("fechaTramitePosterior")),
        noticia_criminal=_texto(d, "noticiaCriminal"),
        solicitud_penal=_texto(d, "solicitudPenal"),
        delitos_adicionales=_lista(d.get("delitosAdicionales")),
        impugnacion=_texto(d, "impugnacion"),
        fecha_impugnacion=a_fecha(d.get("fechaImpugnacion")),
        decision_2da=_texto(d, "decision2da"),
        medida_tutela=_texto(d, "medidaTutela"),
        des_tutela=_texto(d, "desTutela"),
        des_req=a_fecha(d.get("desReq")),
        des_apertura=_texto(d, "desApertura"),
        des_consulta=_texto(d, "desConsulta"),
        cuaderno_inicial=_texto(d, "cuadernoInicial", "Principal"),
        cuadernos=_lista(d.get("cuadernos")),
    )
    p.solicitudes_penales = solicitudes_desde_legacy(d)
    return p


def actuacion_desde_legacy(d: dict) -> Actuacion:
    paso = d.get("pasoIdx")
    ejec = d.get("ejecDias")
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
        tp_tipo=_texto(d, "tpTipo"),
        asignado_a=_texto(d, "asignadoA"),
        tipo_providencia=_texto(d, "tipoProvidencia"),
        modo_cierre=_texto(d, "modoCierre"),
        salida_stat=_texto(d, "salidaStat"),
        entrada_stat=_texto(d, "entradaStat"),
        es_audiencia=bool(d.get("esAudiencia")),
        aud_fecha=a_fecha(d.get("audFecha")),
        aud_hora=_texto(d, "audHora"),
        aud_estado=_texto(d, "audEstado"),
        aud_tipo=_texto(d, "audTipo"),
        aud_causa=_texto(d, "audCausa"),
        aud_inmediata=bool(d.get("audInmediata")),
        cancelacion_de=_texto(d, "cancelacionDe"),
        recurso_tipo=_texto(d, "recursoTipo"),
        recurso_fecha=a_fecha(d.get("recursoFecha")),
        recurso_objeto=_texto(d, "recursoObjeto"),
        rec_traslado=a_fecha(d.get("recTraslado")),
        superior_resultado=_texto(d, "superiorResultado"),
        superior_fecha=a_fecha(d.get("superiorFecha")),
        rec_impug=_texto(d, "recImpug"),
        rec_impug_result=_texto(d, "recImpugResult"),
        rec_impug_fecha=a_fecha(d.get("recImpugFecha")),
        remate_realizado=bool(d.get("remateRealizado")),
        amparo_pobreza_concedido=bool(d.get("amparoPobrezaConcedido")),
        notif_fecha=a_fecha(d.get("notifFecha")),
        notif_forma=_texto(d, "notifForma"),
        ejec_dias=int(ejec) if isinstance(ejec, (int, float)) and ejec > 0 else 3,
    )


def stat_evento_desde_legacy(d: dict) -> StatEvento:
    cantidad = d.get("cantidad")
    return StatEvento(
        id=_texto(d, "id") or nuevo_id(),
        fecha=a_fecha(d.get("fecha")),
        seccion=_texto(d, "seccion"),
        fila=_texto(d, "fila"),
        columna=_texto(d, "columna"),
        cantidad=int(cantidad) if isinstance(cantidad, (int, float)) and cantidad else 1,
        proceso_id=_texto(d, "procesoId") or None,
        nota=_texto(d, "nota"),
    )
