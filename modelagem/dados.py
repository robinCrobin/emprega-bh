"""Leitura da serie agregada gerada pelo pipeline e filtro de trimestres fechados.

Contrato de entrada (docs/DADOS_E_INTEGRACAO.md):
nome_padronizado, codigo_cbo, status_validacao, quarter (AAAA-TN), vacancies.
Lacunas NAO viram zero: um trimestre sem linha para a ocupacao fica ausente.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_PADRAO = RAIZ / 'data' / 'processed' / 'vagas_por_ocupacao_trimestre.csv'
MANIFESTO_COLETA_PADRAO = RAIZ / 'reports' / 'local' / 'vagas_ckan_manifest.json'

COLUNAS_OBRIGATORIAS = ('nome_padronizado', 'codigo_cbo', 'status_validacao', 'quarter', 'vacancies')
PADRAO_TRIMESTRE = re.compile(r'^(\d{4})-T([1-4])$')
PADRAO_CBO = re.compile(r'^\d{6}$')


class ErroDados(ValueError):
    """Arquivo de entrada fora do contrato; nada deve ser treinado com ele."""


def indice_trimestre(ano: int, trimestre: int) -> int:
    """Indice sequencial: trimestres consecutivos diferem em exatamente 1."""
    return ano * 4 + (trimestre - 1)


def trimestre_de_indice(indice: int) -> tuple[int, int]:
    return indice // 4, indice % 4 + 1


def rotulo(indice: int) -> str:
    ano, trimestre = trimestre_de_indice(indice)
    return f'{ano}-T{trimestre}'


def ultimo_trimestre_fechado(referencia: date) -> int:
    """Ultimo trimestre completamente encerrado antes da data de referencia.

    Um trimestre em andamento tem contagem parcial (ex.: 2026-T4 coletado em
    27/11/2026 tinha 2 vagas) e distorceria treino e previsao.
    """
    atual = indice_trimestre(referencia.year, (referencia.month - 1) // 3 + 1)
    return atual - 1


def data_referencia_da_coleta(manifesto: Path) -> date | None:
    """Data da coleta CKAN registrada pelo pipeline (campo collected_at)."""
    if not manifesto.exists():
        return None
    try:
        coletado = json.loads(manifesto.read_text(encoding='utf-8'))['collected_at']
        return datetime.fromisoformat(coletado).date()
    except (KeyError, ValueError, TypeError) as erro:
        raise ErroDados(f'Manifesto de coleta sem collected_at valido: {manifesto}') from erro


def sha256_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


@dataclass
class ResumoLeitura:
    linhas_lidas: int = 0
    linhas_sem_cbo: int = 0
    linhas_nao_validadas: int = 0
    linhas_cbo_invalido: int = 0
    exemplos_cbo_invalido: list[str] = field(default_factory=list)
    linhas_consolidadas: int = 0
    cbos_com_varios_nomes: int = 0
    linhas_trimestre_aberto: int = 0
    trimestres_abertos: list[str] = field(default_factory=list)


def carregar_vagas(caminho: Path) -> tuple[pd.DataFrame, ResumoLeitura]:
    """Le e valida o CSV agregado.

    Retorna colunas: codigo_cbo (texto, 6 digitos), nome_padronizado, indice, vagas.
    Linhas sem CBO, com CBO fora do padrao (ex.: dois codigos '765240;991310')
    ou nao validadas sao descartadas e contadas: o CBO de 6 digitos e a chave
    usada pelo banco e pela API para localizar a previsao.

    O contrato exige uma linha por (CBO, trimestre), mas o pipeline pode emitir
    varias quando um CBO tem mais de um nome padronizado. Nesse caso as vagas
    sao somadas por CBO e trimestre, e o nome com mais vagas vira o descritivo.
    """
    if not caminho.exists():
        raise ErroDados(f'Arquivo nao encontrado: {caminho}. Execute pipeline/ckan_vagas.py.')
    bruto = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding='utf-8')
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in bruto.columns]
    if faltando:
        raise ErroDados(f'Colunas ausentes no arquivo: {faltando}')
    resumo = ResumoLeitura(linhas_lidas=len(bruto))
    bruto = bruto.apply(lambda coluna: coluna.str.strip())

    sem_cbo = bruto['codigo_cbo'] == ''
    resumo.linhas_sem_cbo = int(sem_cbo.sum())
    nao_validado = ~sem_cbo & (bruto['status_validacao'] != 'validado')
    resumo.linhas_nao_validadas = int(nao_validado.sum())
    dados = bruto[~sem_cbo & ~nao_validado].copy()

    cbo_invalido = ~dados['codigo_cbo'].str.fullmatch(PADRAO_CBO)
    resumo.linhas_cbo_invalido = int(cbo_invalido.sum())
    resumo.exemplos_cbo_invalido = sorted(dados.loc[cbo_invalido, 'codigo_cbo'].unique())[:10]
    dados = dados[~cbo_invalido]
    partes = dados['quarter'].str.extract(PADRAO_TRIMESTRE)
    if partes.isna().any(axis=None):
        invalido = dados.loc[partes.isna().any(axis=1), 'quarter'].iloc[0]
        raise ErroDados(f'Trimestre fora do formato AAAA-TN: {invalido!r}')
    vagas = pd.to_numeric(dados['vacancies'], errors='coerce')
    if vagas.isna().any() or (vagas < 0).any() or (vagas % 1 != 0).any():
        raise ErroDados('Coluna vacancies precisa conter inteiros nao negativos.')

    dados = pd.DataFrame({
        'codigo_cbo': dados['codigo_cbo'],
        'nome_padronizado': dados['nome_padronizado'],
        'indice': partes[0].astype(int) * 4 + partes[1].astype(int) - 1,
        'vagas': vagas.astype(int),
    })
    resumo.linhas_consolidadas = int(dados.duplicated(['codigo_cbo', 'indice']).sum())
    nomes = (dados.groupby(['codigo_cbo', 'nome_padronizado'], as_index=False)['vagas'].sum()
             .sort_values(['codigo_cbo', 'vagas', 'nome_padronizado'], ascending=[True, False, True])
             .drop_duplicates('codigo_cbo').set_index('codigo_cbo')['nome_padronizado'])
    resumo.cbos_com_varios_nomes = int((dados.groupby('codigo_cbo')['nome_padronizado'].nunique() > 1).sum())
    dados = dados.groupby(['codigo_cbo', 'indice'], as_index=False)['vagas'].sum()
    dados.insert(1, 'nome_padronizado', dados['codigo_cbo'].map(nomes))
    return dados.sort_values(['codigo_cbo', 'indice']).reset_index(drop=True), resumo


def remover_trimestres_abertos(dados: pd.DataFrame, ultimo_fechado: int,
                               resumo: ResumoLeitura) -> pd.DataFrame:
    abertos = dados['indice'] > ultimo_fechado
    resumo.linhas_trimestre_aberto = int(abertos.sum())
    resumo.trimestres_abertos = [rotulo(i) for i in sorted(dados.loc[abertos, 'indice'].unique())]
    return dados[~abertos].reset_index(drop=True)
