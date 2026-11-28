"""A12: metricas MAE/RMSE e validacao temporal com janela expansiva."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from modelagem.dados import rotulo
from modelagem.modelos import Candidato
from modelagem.variaveis import ALVO, VARIAVEIS


def metricas(reais, previstos) -> dict:
    reais, previstos = np.asarray(reais, dtype=float), np.asarray(previstos, dtype=float)
    return {'mae': float(mean_absolute_error(reais, previstos)),
            'rmse': float(root_mean_squared_error(reais, previstos)),
            'exemplos': int(len(reais))}


def prever(modelo, exemplos: pd.DataFrame) -> np.ndarray:
    """Previsao limitada a zero (vagas nao podem ser negativas; o banco exige >= 0)."""
    return np.clip(modelo.predict(exemplos[VARIAVEIS].to_numpy(dtype=float)), 0, None)


def ajustar(candidato: Candidato, exemplos: pd.DataFrame):
    modelo = candidato.criar()
    modelo.fit(exemplos[VARIAVEIS].to_numpy(dtype=float), exemplos[ALVO].to_numpy(dtype=float))
    return modelo


def validacao_expansiva(candidato: Candidato, treino: pd.DataFrame, dobras: int) -> dict:
    """Backtesting dentro do treino: para cada um dos ultimos `dobras` trimestres
    alvo q, ajusta com alvos < q e avalia em q. O conjunto de teste nao e usado.
    """
    alvos = sorted(treino['alvo_indice'].unique())
    if len(alvos) <= dobras:
        raise ValueError(f'Treino com {len(alvos)} trimestres alvo; insuficiente para {dobras} dobras.')
    reais, previstos, por_dobra = [], [], []
    for q in alvos[-dobras:]:
        ajuste, validacao = treino[treino['alvo_indice'] < q], treino[treino['alvo_indice'] == q]
        estimativa = prever(ajustar(candidato, ajuste), validacao)
        reais.append(validacao[ALVO].to_numpy())
        previstos.append(estimativa)
        por_dobra.append({'periodo_validacao': rotulo(q), 'exemplos_ajuste': len(ajuste),
                          **metricas(validacao[ALVO], estimativa)})
    return {'candidato': candidato.chave, 'familia': candidato.familia,
            'parametros': candidato.parametros,
            **metricas(np.concatenate(reais), np.concatenate(previstos)), 'dobras': por_dobra}


def melhor(resultados: list[dict]) -> dict:
    """Menor MAE agregado na validacao; RMSE desempata."""
    return min(resultados, key=lambda r: (round(r['mae'], 9), round(r['rmse'], 9)))
