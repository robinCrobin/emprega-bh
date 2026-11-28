"""A08: carga idempotente do CSV agregado (contrato da Roberta) no PostgreSQL.

Contrato do CSV (docs/DADOS_E_INTEGRACAO.md): nome_padronizado, codigo_cbo,
status_validacao, quarter (AAAA-TN) e vacancies. A identidade da ocupação é o
codigo_cbo. Lacunas NÃO são preenchidas com zero.

O pipeline agrega por nome + CBO + trimestre; por isso um mesmo CBO pode vir com
nomes diferentes e mais de uma linha por trimestre. A carga SOMA as vagas por
(CBO, trimestre) e adota como nome o que tem mais vagas no total (empate: ordem
alfabética). Linhas totalmente repetidas (mesmo CBO, nome e trimestre) indicam
erro no arquivo e continuam sendo rejeitadas.
"""
import csv
import re
from collections import defaultdict
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
    linhas_consolidadas: int = 0  # linhas de nomes alternativos somadas ao mesmo CBO


def ler_csv(caminho: Path) -> tuple[dict[str, str], list[tuple[str, int, int, int]], int, int]:
    """Valida o CSV; devolve (nome por CBO, linhas (cbo, ano, tri, vagas), ignoradas, consolidadas)."""
    vagas_por_nome: dict[tuple[str, str], int] = defaultdict(int)
    somadas: dict[tuple[str, int, int], int] = defaultdict(int)
    vistos: set[tuple[str, str, int, int]] = set()
    ignoradas = 0
    total_linhas = 0
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
            ano, tri = int(casado.group(1)), int(casado.group(2))
            repetida = (cbo, nome, ano, tri)
            if repetida in vistos:
                raise ErroCarga(f'Linha {numero}: combinação CBO/nome/trimestre duplicada: {repetida}')
            vistos.add(repetida)
            vagas_por_nome[(cbo, nome)] += vagas
            somadas[(cbo, ano, tri)] += vagas
            total_linhas += 1
    # Nome adotado por CBO: o de maior total de vagas; empate resolvido por ordem alfabética.
    escolhido: dict[str, tuple[int, str]] = {}
    for (cbo, nome), total in vagas_por_nome.items():
        atual = escolhido.get(cbo)
        if atual is None or (-total, nome) < (-atual[0], atual[1]):
            escolhido[cbo] = (total, nome)
    nomes = {cbo: nome for cbo, (_, nome) in escolhido.items()}
    linhas = [(cbo, ano, tri, vagas) for (cbo, ano, tri), vagas in sorted(somadas.items())]
    return nomes, linhas, ignoradas, total_linhas - len(linhas)


def carregar_csv(conexao: psycopg.Connection, caminho: Path) -> ResumoCarga:
    """Upsert em transação única: reexecutar o mesmo arquivo não duplica dados."""
    nomes, linhas, ignoradas, consolidadas = ler_csv(caminho)
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
    return ResumoCarga(len(nomes), len(linhas), ignoradas, consolidadas)
