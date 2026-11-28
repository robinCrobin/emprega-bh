"""A10: variaveis de entrada e divisao treino/teste temporal; A12: regra minima.

Cada exemplo supervisionado e (ocupacao, trimestre alvo):
- defasagem_1..defasagem_4: vagas nos 4 trimestres imediatamente anteriores ao
  alvo (defasagem_1 = trimestre anterior). Os quatro precisam existir na serie;
  lacunas nao sao preenchidas com zero (docs/PLANO_TESTES.md).
- trimestre_2..trimestre_4: trimestre do ano do alvo em codificacao one-hot
  (o 1o trimestre e a referencia), para capturar sazonalidade.
- alvo: vagas observadas no trimestre alvo.

Nenhuma variavel usa informacao do trimestre alvo ou posterior a ele, e a regra
de historico minimo e avaliada com os dados disponiveis ANTES do alvo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from modelagem.dados import rotulo, trimestre_de_indice

JANELA = 4
PADRAO_MINIMO_TRIMESTRES = 8
COLUNAS_DEFASAGEM = [f'defasagem_{k}' for k in range(1, JANELA + 1)]
COLUNAS_TRIMESTRE = ['trimestre_2', 'trimestre_3', 'trimestre_4']
VARIAVEIS = COLUNAS_DEFASAGEM + COLUNAS_TRIMESTRE
ALVO = 'vagas'


def minimo_trimestres(valor: int | str | None = None) -> int:
    """Historico minimo (A12). Mesma variavel de ambiente usada pela API.

    Nunca menor que JANELA: sem 4 trimestres anteriores nao ha defasagens.
    """
    bruto = valor if valor is not None else os.getenv('MIN_TRIMESTRES_PREVISAO', PADRAO_MINIMO_TRIMESTRES)
    try:
        return max(int(bruto), JANELA)
    except (TypeError, ValueError):
        return PADRAO_MINIMO_TRIMESTRES


def avaliar_elegibilidade(indices_com_dados: set[int], alvo: int, minimo: int) -> tuple[bool, str | None]:
    """A12: decide se ha historico suficiente para prever o trimestre `alvo`.

    Regras, ambas obrigatorias:
    1. pelo menos `minimo` (padrao 8) trimestres com dados antes do alvo;
    2. os 4 trimestres imediatamente anteriores ao alvo presentes na serie.
    """
    anteriores = sum(1 for i in indices_com_dados if i < alvo)
    if anteriores < minimo:
        return False, (f'Historico insuficiente: {anteriores} trimestre(s) com dados antes de '
                       f'{rotulo(alvo)}; o minimo para gerar previsao e {minimo}.')
    faltando = [rotulo(alvo - k) for k in range(JANELA, 0, -1) if alvo - k not in indices_com_dados]
    if faltando:
        return False, (f'Sem dados em {", ".join(faltando)}; a previsao usa os 4 trimestres '
                       'anteriores ao alvo e lacunas nao sao tratadas como zero vagas.')
    return True, None


def linha_variaveis(vagas_por_indice: dict[int, int], alvo: int) -> dict[str, int]:
    _, trimestre = trimestre_de_indice(alvo)
    linha = {f'defasagem_{k}': vagas_por_indice[alvo - k] for k in range(1, JANELA + 1)}
    linha.update({f'trimestre_{t}': int(trimestre == t) for t in (2, 3, 4)})
    return linha


def _series(dados: pd.DataFrame):
    for cbo, grupo in dados.groupby('codigo_cbo', sort=True):
        yield cbo, grupo['nome_padronizado'].iloc[-1], dict(zip(grupo['indice'], grupo['vagas']))


def montar_exemplos(dados: pd.DataFrame, minimo: int) -> pd.DataFrame:
    """Um exemplo por trimestre observado que seja elegivel na data do alvo."""
    linhas = []
    for cbo, _, serie in _series(dados):
        indices = set(serie)
        for alvo in sorted(indices):
            if avaliar_elegibilidade(indices, alvo, minimo)[0]:
                linhas.append({'codigo_cbo': cbo, 'alvo_indice': alvo, 'periodo_alvo': rotulo(alvo),
                               **linha_variaveis(serie, alvo), ALVO: serie[alvo]})
    colunas = ['codigo_cbo', 'alvo_indice', 'periodo_alvo', *VARIAVEIS, ALVO]
    return pd.DataFrame(linhas, columns=colunas)


def montar_entrada_previsao(dados: pd.DataFrame, alvo: int, minimo: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Variaveis para prever `alvo` (proximo trimestre apos o ultimo fechado).

    Retorna (elegiveis, sem_previsao com motivo). A exigencia das 4 defasagens
    garante que so ocupacoes com dado no ultimo trimestre fechado recebem
    previsao, coincidindo com a chave que a API consulta (trimestre seguinte ao
    ultimo periodo da ocupacao).
    """
    elegiveis, sem_previsao = [], []
    for cbo, nome, serie in _series(dados):
        indices = set(serie)
        ok, motivo = avaliar_elegibilidade(indices, alvo, minimo)
        base = {'codigo_cbo': cbo, 'nome_padronizado': nome,
                'trimestres_historico': sum(1 for i in indices if i < alvo)}
        if ok:
            elegiveis.append({**base, **linha_variaveis(serie, alvo)})
        else:
            sem_previsao.append({**base, 'motivo': motivo})
    return (pd.DataFrame(elegiveis, columns=['codigo_cbo', 'nome_padronizado', 'trimestres_historico', *VARIAVEIS]),
            pd.DataFrame(sem_previsao, columns=['codigo_cbo', 'nome_padronizado', 'trimestres_historico', 'motivo']))


@dataclass
class DivisaoTemporal:
    treino: pd.DataFrame
    teste: pd.DataFrame
    periodos_treino: tuple[str, str]
    periodos_teste: tuple[str, str]


def divisao_temporal(exemplos: pd.DataFrame, trimestres_teste: int) -> DivisaoTemporal:
    """Reserva os ultimos `trimestres_teste` trimestres alvo para teste.

    Corte por trimestre alvo, nunca por linha ou sorteio: todo exemplo de treino
    e anterior a todo exemplo de teste.
    """
    alvos = sorted(exemplos['alvo_indice'].unique())
    if len(alvos) <= trimestres_teste:
        raise ValueError(f'Sao necessarios mais de {trimestres_teste} trimestres alvo distintos; '
                         f'ha {len(alvos)}.')
    corte = alvos[-trimestres_teste]
    treino = exemplos[exemplos['alvo_indice'] < corte].reset_index(drop=True)
    teste = exemplos[exemplos['alvo_indice'] >= corte].reset_index(drop=True)
    return DivisaoTemporal(
        treino=treino, teste=teste,
        periodos_treino=(rotulo(alvos[0]), rotulo(alvos[-trimestres_teste - 1])),
        periodos_teste=(rotulo(corte), rotulo(alvos[-1])),
    )
