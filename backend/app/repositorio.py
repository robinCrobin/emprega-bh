"""Repositório: consultas SQL parametrizadas (somente leitura, sem regras de negócio)."""
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from app.banco.normalizacao import normalizar_texto


def buscar_ocupacoes(conexao: psycopg.Connection, texto: str, limite: int) -> list[dict]:
    """RF01: busca por trechos do nome, sem distinção de acento ou caixa.

    Todas as palavras digitadas precisam aparecer no nome (ordem livre).
    """
    termo = normalizar_texto(texto)
    palavras = termo.split()
    if not palavras:
        return []
    condicoes = ' AND '.join(['nome_normalizado LIKE %s'] * len(palavras))
    parametros = [f'%{p}%' for p in palavras] + [f'{termo}%', limite]
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f'SELECT id, nome, codigo_cbo FROM ocupacao WHERE {condicoes} '
            'ORDER BY (nome_normalizado LIKE %s) DESC, nome_normalizado, id LIMIT %s',
            parametros,
        )
        return cur.fetchall()


def obter_ocupacao(conexao: psycopg.Connection, ocupacao_id: int) -> Optional[dict]:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT id, nome, codigo_cbo FROM ocupacao WHERE id = %s', (ocupacao_id,))
        return cur.fetchone()


def obter_serie(conexao: psycopg.Connection, ocupacao_id: int) -> list[dict]:
    """RF02: série histórica em ordem cronológica."""
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT ano, trimestre, quantidade_vagas FROM vagas_trimestre '
            'WHERE ocupacao_id = %s ORDER BY ano, trimestre',
            (ocupacao_id,),
        )
        return cur.fetchall()


def contar_trimestres(conexao: psycopg.Connection, ocupacao_id: int) -> int:
    with conexao.cursor() as cur:
        cur.execute('SELECT count(*) FROM vagas_trimestre WHERE ocupacao_id = %s', (ocupacao_id,))
        return cur.fetchone()[0]


def obter_previsao(conexao: psycopg.Connection, ocupacao_id: int,
                   ano_alvo: int, trimestre_alvo: int) -> Optional[dict]:
    """Previsão já gravada para o trimestre alvo, ou None (nunca calcula nada)."""
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'SELECT ano_alvo, trimestre_alvo, quantidade_prevista, algoritmo, gerado_em '
            'FROM previsao WHERE ocupacao_id = %s AND ano_alvo = %s AND trimestre_alvo = %s',
            (ocupacao_id, ano_alvo, trimestre_alvo),
        )
        return cur.fetchone()
