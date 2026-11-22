"""Base de infraestrutura. Endpoints de negocio pertencem a frente backend."""
import os

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import database_options  # noqa: F401 (mantido para compatibilidade)
from app.rotas import ocupacoes

app = FastAPI(
    title='EmpregaBH',
    version='0.2.0',
    description='API de consulta de vagas por ocupação em Belo Horizonte (dados da PBH). '
                'Somente leitura de dados agregados e previsões já gravadas no PostgreSQL.',
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv(
        'API_CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',') if v.strip()],
    allow_credentials=False,
    allow_methods=['GET'],
    allow_headers=['Content-Type'],
)


@app.get('/healthz', tags=['Infraestrutura'])
def health():
    return {'status': 'ok', 'service': 'empregabh-api'}


@app.get('/readyz', tags=['Infraestrutura'])
def ready():
    try:
        with psycopg.connect(**database_options()) as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
    except psycopg.Error:
        return JSONResponse(status_code=503, content={'status': 'indisponivel'})
    return {'status': 'ok', 'database': 'ok'}


app.include_router(ocupacoes.router)


@app.exception_handler(RequestValidationError)
async def erro_validacao(request: Request, exc: RequestValidationError):
    campos = sorted({str(e['loc'][-1]) for e in exc.errors()})
    return JSONResponse(status_code=422, content={'detail': 'Parâmetros inválidos: ' + ', '.join(campos) + '.'})


@app.exception_handler(psycopg.Error)
async def erro_banco(request: Request, exc: psycopg.Error):
    return JSONResponse(status_code=503, content={'detail': 'Serviço temporariamente indisponível.'})