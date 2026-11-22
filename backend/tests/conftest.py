"""Fixtures: PostgreSQL real com SCHEMA isolado e descartável por sessão de testes.

Usa a mesma configuração de conexão do projeto (.env / PG*). O schema `teste_*`
é criado no início e removido ao final, sem tocar nas tabelas reais do banco.
"""
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.banco.migracoes import aplicar_migracoes  # noqa: E402
from app.config import database_options  # noqa: E402
from app.main import app  # noqa: E402
from app.rotas.ocupacoes import obter_conexao  # noqa: E402


@pytest.fixture(scope='session')
def conexao_teste():
    schema = f'teste_{uuid.uuid4().hex[:8]}'
    try:
        admin = psycopg.connect(**database_options(), autocommit=True)
    except psycopg.OperationalError as erro:
        pytest.skip(f'PostgreSQL indisponível para testes de banco: {type(erro).__name__}')
    admin.execute(f'CREATE SCHEMA {schema}')
    conexao = psycopg.connect(**database_options(), autocommit=True,
                              options=f'-c search_path={schema},public')
    aplicar_migracoes(conexao)
    yield conexao
    conexao.close()
    admin.execute(f'DROP SCHEMA {schema} CASCADE')
    admin.close()


@pytest.fixture()
def banco(conexao_teste):
    """Banco limpo a cada teste."""
    conexao_teste.execute('TRUNCATE ocupacao, metrica_modelo RESTART IDENTITY CASCADE')
    return conexao_teste


@pytest.fixture()
def cliente(banco):
    app.dependency_overrides[obter_conexao] = lambda: banco
    yield TestClient(app)
    app.dependency_overrides.clear()


def inserir_ocupacao(banco, nome, cbo, trimestres):
    """Cria ocupação FICTÍCIA com a lista de vagas por trimestre a partir de 2021-T1."""
    from app.banco.normalizacao import normalizar_texto
    oid = banco.execute(
        'INSERT INTO ocupacao (codigo_cbo, nome, nome_normalizado) VALUES (%s,%s,%s) RETURNING id',
        (cbo, nome, normalizar_texto(nome))).fetchone()[0]
    for i, vagas in enumerate(trimestres):
        banco.execute(
            'INSERT INTO vagas_trimestre (ocupacao_id, ano, trimestre, quantidade_vagas) VALUES (%s,%s,%s,%s)',
            (oid, 2021 + i // 4, i % 4 + 1, vagas))
    return oid
