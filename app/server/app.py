from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

DOC_PRUEBA = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Constancia de prueba</title>
<style>@page{size:Letter;margin:2.2cm 2.6cm}body{font-family:"Times New Roman",Georgia,serif;font-size:12.5pt;line-height:1.5}
.ti{text-align:center;font-weight:bold;text-decoration:underline;margin:6pt 0 14pt}.cuerpo{text-align:justify}</style></head>
<body><div class="ti">CONSTANCIA SECRETARIAL</div>
<p><b>Proceso:</b> Ejecutivo singular</p><p><b>Radicado:</b> 54-172-40-89-001-2019-00327-00</p>
<div class="cuerpo">Se deja constancia que en la fecha se recibió memorial en el proceso de la referencia,
el cual se agrega al expediente para lo de su cargo. Documento de prueba de impresión.</div>
<p>Chinácota, 30 de septiembre de 2026.</p></body></html>"""


def create_app() -> FastAPI:
    app = FastAPI(title="Control de Procesos", docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/spike/doc", response_class=HTMLResponse)
    def spike_doc():
        return DOC_PRUEBA

    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
