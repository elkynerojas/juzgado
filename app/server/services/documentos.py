import base64
from datetime import date
from html import escape

from app.server.domain.fechas_letras import fecha_larga
from app.server.domain.plantillas import ciudad_corta, radicado_completo

CSS = (
    '@page{size:Letter;margin:2.2cm 2.6cm}html,body{margin:0}body{font-family:"Times New Roman",Georgia,serif;'
    "color:#000;font-size:12.5pt;line-height:1.5}.mem{margin-bottom:16pt}.mem img{width:100%;max-width:17cm}"
    ".jz{text-align:center;font-weight:bold;font-size:11pt;margin-bottom:18pt}.ti{text-align:center;font-weight:bold;"
    "text-decoration:underline;margin:6pt 0 14pt;font-size:13pt}.ref p{margin:0 0 2pt}.cuerpo{text-align:justify;"
    "margin:14pt 0}.lugar{margin:16pt 0 22pt}.firma img{max-width:8cm;height:auto}.fnom{font-weight:bold;margin:0}"
    ".fcar{margin:0}"
)


def data_uri(contenido: bytes, mime: str) -> str:
    return f"data:{mime or 'image/png'};base64,{base64.b64encode(contenido).decode()}"


def html_documento(
    *, proceso, cuerpo: str, fecha: date, juzgado: str, ciudad: str, prefijo: str, membrete: str | None, firmante
) -> str:
    """Constancia o pase listo para imprimir. `membrete` es un data URI; `firmante` puede ser None."""
    if membrete:
        encabezado = f'<div class="mem"><img src="{membrete}"></div>'
    else:
        encabezado = f'<div class="jz">{escape(juzgado)}<br>{escape(ciudad)}</div>'
    if firmante and firmante.firma:
        firma = f'<div class="firma"><img src="{data_uri(firmante.firma, firmante.firma_mime)}"></div>'
    else:
        nombre = escape(firmante.nombre) if firmante else ""
        cargo = escape(firmante.cargo) if firmante else ""
        firma = f'<div style="height:56px"></div><p class="fnom">{nombre}</p><p class="fcar">{cargo}</p>'
    cuerpo_html = escape(cuerpo).replace("\n", "<br>")
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        f"<title>Constancia {escape(proceso.radicado or '')}</title><style>{CSS}</style></head><body>"
        f'{encabezado}<div class="ti">CONSTANCIA SECRETARIAL</div>'
        f'<div class="ref"><p><b>Proceso:</b> {escape(proceso.clase or "")}</p>'
        f"<p><b>Radicado:</b> {escape(radicado_completo(prefijo, proceso.radicado))}</p></div>"
        f'<div class="cuerpo">{cuerpo_html}</div>'
        f'<div class="lugar">{escape(ciudad_corta(ciudad))}, {fecha_larga(fecha)}.</div>'
        f"{firma}</body></html>"
    )
