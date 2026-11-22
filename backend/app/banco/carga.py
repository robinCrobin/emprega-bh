"""A08: carga idempotente do CSV agregado (contrato da Roberta) no PostgreSQL.

Contrato do CSV (docs/DADOS_E_INTEGRACAO.md): nome_padronizado, codigo_cbo,
status_validacao, quarter (AAAA-TN) e vacancies. A chave lógica é
(codigo_cbo, quarter). Lacunas NÃO são preenchidas com zero.
"""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.banco.normalizacao import normalizar_texto

COLUNAS_OBRIGATORIAS = ('nome_padronizado', 'codigo_cbo', 'status_validacao', 'quarter', 'vacancies')
_RE_TRIMESTRE = re.compile(r'^(\d{4})-T([1-4])$')
_RE_CBO = re.compile(r'^\d{6}$')


class ErroCarga(ValueError):
    """Arquivo fora do contrato; nada é gravado."""


@dataclass
class ResumoCarga:
    ocupacoes: int
    linhas_vagas: int
    linhas_ignoradas: int


def ler_csv(caminho: Path) -> tuple[dict[str, str], list[tuple[str, int, int, int]], int]:
    """Valida o CSV e devolve (nomes por CBO, linhas (cbo, ano, tri, vagas), ignoradas)."""
    nomes: dict[str, str] = {}
    linhas: list[tuple[str, int, int, int]] = []
    vistos: set[tuple[str, int, int]] = set()
    ignoradas = 0
    with caminho.open('r', newline='', encoding='utf-8-sig') as origem:
        leitor = csv.DictReader(origem)
        faltando = set(COLUNAS_OBRIGATORIAS) - set(leitor.fieldnames or ())
        if faltando:
            raise ErroCarga(f'Colunas ausentes no CSV: {sorted(faltando)}')
        for numero, linha in enumerate(leitor, start=2):
            if (linha['status_validacao'] or '').strip().lower() != 'validado':
                ignoradas += 1
                continue
            cbo = (linha['codigo_cbo'] or '').strip()
            nome = ' '.join((linha['nome_padronizado'] or '').split())
            if not _RE_CBO.match(cbo):
                raise ErroCarga(f'Linha {numero}: codigo_cbo inválido: {cbo!r}')
            if not nome:
                raise ErroCarga(f'Linha {numero}: nome_padronizado vazio')
            casado = _RE_TRIMESTRE.match((linha['quarter'] or '').strip())
            if not casado:
                raise ErroCarga(f'Linha {numero}: quarter fora do formato AAAA-TN: {linha["quarter"]!r}')
            try:
                vagas = int((linha['vacancies'] or '').strip())
            except ValueError:
                raise ErroCarga(f'Linha {numero}: vacancies não é inteiro: {linha["vacancies"]!r}') from None
            if vagas < 0:
                raise ErroCarga(f'Linha {numero}: vacancies negativo')
            if nomes.setdefault(cbo, nome) != nome:
                raise ErroCarga(f'Linha {numero}: CBO {cbo} com dois nomes diferentes')
            chave = (cbo, int(casado.group(1)), int(casado.group(2)))
            if chave in vistos:
                raise ErroCarga(f'Linha {numero}: combinação CBO/trimestre duplicada: {chave}')
            vistos.add(chave)
            linhas.append((*chave, vagas))
    return nomes, linhas, ignoradas


def carregar_csv(conexao: psycopg.Connection, caminho: Path) -> ResumoCarga:
    """Upsert em transação única: reexecutar o mesmo arquivo não duplica dados."""
    nomes, linhas, ignoradas = ler_csv(caminho)
    with conexao.transaction(), conexao.cursor() as cur:
        ids: dict[str, int] = {}
        for cbo, nome in nomes.items():
            cur.execute(
                'INSERT INTO ocupacao (codigo_cbo, nome, nome_normalizado) VALUES (%s, %s, %s) '
                'ON CONFLICT (codigo_cbo) DO UPDATE '
                'SET nome = EXCLUDED.nome, nome_normalizado = EXCLUDED.nome_normalizado '
                'RETURNING id',
                (cbo, nome, normalizar_texto(nome)),
            )
            ids[cbo] = cur.fetchone()[0]
        cur.executemany(
            'INSERT INTO vagas_trimestre (ocupacao_id, ano, trimestre, quantidade_vagas) '
            'VALUES (%s, %s, %s, %s) '
            'ON CONFLICT (ocupacao_id, ano, trimestre) '
            'DO UPDATE SET quantidade_vagas = EXCLUDED.quantidade_vagas',
            [(ids[cbo], ano, tri, vagas) for cbo, ano, tri, vagas in linhas],
        )
    return ResumoCarga(len(nomes), len(linhas), ignoradas)
