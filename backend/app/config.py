"""Configuração lida de variáveis de ambiente (sem segredos no código)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)

# Número mínimo de trimestres com dados para gerar previsão e tendência (RF05).
PADRAO_MINIMO_TRIMESTRES = 8


def database_options():
    """Parâmetros de conexão com o PostgreSQL."""
    return {
        'host': os.getenv('PGHOST', '127.0.0.1'),
        'port': int(os.getenv('PGPORT', os.getenv('DB_PORT', '5433'))),
        'dbname': os.getenv('POSTGRES_DB', 'empregabh'),
        'user': os.getenv('POSTGRES_USER', 'empregabh'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'connect_timeout': 2,
    }


def minimo_trimestres() -> int:
    """Histórico mínimo configurável (variável MIN_TRIMESTRES_PREVISAO, padrão 8)."""
    try:
        valor = int(os.getenv('MIN_TRIMESTRES_PREVISAO', PADRAO_MINIMO_TRIMESTRES))
    except ValueError:
        return PADRAO_MINIMO_TRIMESTRES
    return max(valor, 2)


def limite_maximo_busca() -> int:
    try:
        return max(int(os.getenv('BUSCA_LIMITE_MAXIMO', '50')), 1)
    except ValueError:
        return 50
