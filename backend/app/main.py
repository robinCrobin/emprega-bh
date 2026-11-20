"""Base de infraestrutura. Endpoints de negocio pertencem a frente backend."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)


def database_options():
    return {
        'host': os.getenv('PGHOST', '127.0.0.1'),
        'port': int(os.getenv('PGPORT', os.getenv('DB_PORT', '5433'))),
        'dbname': os.getenv('POSTGRES_DB', 'empregabh'),
        'user': os.getenv('POSTGRES_USER', 'empregabh'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'connect_timeout': 2,
    }


app = FastAPI(title='EmpregaBH', version='0.1.0')
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
