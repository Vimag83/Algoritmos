import asyncio
import subprocess
import os
import sys
import traceback
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import importlib

# Importar la lógica de los requerimientos de forma dinámica
analizador_similitud = importlib.import_module("app.2_similitud_texto.analizador_similitud")

app = FastAPI()

# --- Configuración de rutas ---
BASE_DIR = Path(__file__).resolve().parent.parent
templates_dir = os.path.join(str(BASE_DIR), "frontend", "templates")
print(f"DEBUG: La ruta de los templates es: {templates_dir}")
templates = Jinja2Templates(directory=templates_dir)

PYTHON_EXECUTABLE = sys.executable

# PROJECT_ROOT → carpeta analisis_bibliometrico
PROJECT_ROOT = BASE_DIR

# Ruta al script de scraping
SCRAPER_SCRIPT_PATH = PROJECT_ROOT / "backend" / "app" / "1_procesamiento_datos" / "web_scraper.py"
SCRAPER_WORKING_DIR = SCRAPER_SCRIPT_PATH.parent

# --- Modelos de Datos (Pydantic) ---
class AnalisisSimilitudRequest(BaseModel):
    article_ids: List[str]
    algoritmo: str

# --- Rutas y Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- Endpoints para Requerimiento 1 ---
@app.post("/run-scraper")
async def run_scraper(
    database: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Inicia el script de scraping en un proceso de segundo plano.
    """
    command = [
        PYTHON_EXECUTABLE,
        "-u",
        str(SCRAPER_SCRIPT_PATH),
        "--database",
        database,
        "--email",
        email
    ]

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=str(SCRAPER_WORKING_DIR)
        )
        process.stdin.write(f"{password}\n".encode("utf-8"))
        process.stdin.close()
        message = f"Proceso de scraping para '{database}' iniciado."
        return JSONResponse(content={"message": message}, status_code=202)

    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"--- ERROR CRÍTICO AL INICIAR EL SUBPROCESO ---\n{tb_str}"
        print(error_message)
        return JSONResponse(content={"error": error_message}, status_code=500)

# --- Endpoints para Requerimiento 2 ---
@app.get("/articulos")
async def get_articulos():
    """
    Carga y devuelve la lista de artículos desde el archivo .bib.
    """
    articulos = analizador_similitud.cargar_articulos()
    if not articulos:
        return JSONResponse(content={"error": "No se pudo cargar la lista de artículos. Asegúrate de haber generado el archivo 'articulos_unicos.bib' primero."}, status_code=404)
    
    articulos_simplificados = [
        {"id": articulo.get('ID', ''), "title": articulo.get('title', 'Sin título')}
        for articulo in articulos
    ]
    return JSONResponse(content=articulos_simplificados)

@app.post("/analizar-similitud")
async def analizar_similitud(request_data: AnalisisSimilitudRequest):
    """
    Recibe dos IDs de artículos y el algoritmo a usar, y calcula la similitud.
    """
    if len(request_data.article_ids) != 2:
        return JSONResponse(content={"error": "Por favor, selecciona exactamente dos artículos para comparar."}, status_code=400)

    id1 = request_data.article_ids[0]
    id2 = request_data.article_ids[1]
    algoritmo = request_data.algoritmo

    articulos = analizador_similitud.cargar_articulos()
    if not articulos:
        return JSONResponse(content={"error": "No se pudo cargar la lista de artículos."}, status_code=500)

    if algoritmo == "levenshtein":
        resultado = analizador_similitud.analizar_similitud_levenshtein(articulos, id1, id2)
    elif algoritmo == "coseno":
        resultado = analizador_similitud.analizar_similitud_coseno(articulos, id1, id2)
    elif algoritmo == "jaccard":
        resultado = analizador_similitud.analizar_similitud_jaccard(articulos, id1, id2)
    else:
        return JSONResponse(content={"error": f"Algoritmo '{algoritmo}' no reconocido."}, status_code=400)

    if "error" in resultado:
        return JSONResponse(content=resultado, status_code=404)

    return JSONResponse(content=resultado)


# Para ejecutar la aplicación:
# uvicorn main:app --reload
