PERMISOS: dict[str, str] = {
    "procesos.ver": "Ver procesos y tablero",
    "procesos.crear": "Crear procesos",
    "procesos.editar": "Editar procesos",
    "procesos.eliminar": "Eliminar procesos",
    "procesos.notas": "Editar las notas del proceso",
    "actuaciones.ver": "Ver actuaciones",
    "actuaciones.crear": "Crear actuaciones",
    "actuaciones.editar": "Editar actuaciones",
    "actuaciones.eliminar": "Eliminar actuaciones",
    "documentos.generar": "Generar constancias y pases al despacho",
    "paquetes.ver": "Ver la gestión por paquetes",
    "paquetes.exportar": "Imprimir y exportar listas de paquetes",
    "config.catalogos": "Configurar catálogos",
    "config.terminos": "Configurar términos",
    "config.rutas": "Configurar rutas procesales",
    "config.calendario": "Configurar el calendario judicial",
    "config.plantillas": "Configurar plantillas y firmantes",
    "config.juzgado": "Configurar datos del juzgado y membrete",
    "respaldo.exportar": "Exportar respaldos",
    "respaldo.restaurar": "Restaurar respaldos y cargar datos de ejemplo",
    "respaldo.vaciar": "Vaciar todos los procesos",
    "usuarios.gestionar": "Gestionar usuarios",
    "roles.gestionar": "Gestionar roles y permisos",
    "auditoria.ver": "Ver la auditoría de cambios",
}

ROL_ADMIN = "Administrador"

_LECTURA = ["procesos.ver", "actuaciones.ver", "paquetes.ver"]
_OPERACION = [
    *_LECTURA,
    "procesos.crear",
    "procesos.editar",
    "procesos.notas",
    "actuaciones.crear",
    "actuaciones.editar",
    "documentos.generar",
    "paquetes.exportar",
]

# El rol Administrador es de sistema: siempre tiene todos los permisos y no se edita.
ROLES_SEMILLA: dict[str, tuple[str, list[str]]] = {
    ROL_ADMIN: ("Acceso total al sistema", []),
    "Juez": (
        "Consulta, notas, decisiones y documentos",
        [*_LECTURA, "procesos.notas", "actuaciones.editar", "documentos.generar", "paquetes.exportar"],
    ),
    "Secretario": (
        "Gestión completa de procesos y configuración",
        [
            *_OPERACION,
            "procesos.eliminar",
            "actuaciones.eliminar",
            *(p for p in PERMISOS if p.startswith("config.")),
            "respaldo.exportar",
        ],
    ),
    "Escribiente": ("Registro y trámite de procesos y actuaciones", _OPERACION),
    "Consulta": ("Solo lectura", _LECTURA),
}
