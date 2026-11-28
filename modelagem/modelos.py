"""A11: algoritmos comparados (regressao linear e Random Forest) e referencia."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from modelagem.variaveis import COLUNAS_DEFASAGEM, VARIAVEIS

SEMENTE = 42


class MediaUltimosQuatro(RegressorMixin, BaseEstimator):
    """Referencia ingenua: media das vagas nos 4 trimestres anteriores.

    Nao aprende nada; serve para verificar se os modelos agregam valor
    (proposta de criterio em docs/PLANO_TESTES.md).
    """

    def fit(self, X, y=None):
        self.n_features_in_ = X.shape[1]
        return self

    def predict(self, X):
        posicoes = [VARIAVEIS.index(c) for c in COLUNAS_DEFASAGEM]
        return np.asarray(X, dtype=float)[:, posicoes].mean(axis=1)


@dataclass
class Candidato:
    familia: str           # identificador estavel (regressao_linear, random_forest, ...)
    nome_exibicao: str     # usado no relatorio; o banco recebe `familia`
    parametros: dict = field(default_factory=dict)
    fabrica: Callable[[], BaseEstimator] | None = None

    @property
    def chave(self) -> str:
        if not self.parametros:
            return self.familia
        return self.familia + '(' + ', '.join(f'{k}={v}' for k, v in self.parametros.items()) + ')'

    def criar(self) -> BaseEstimator:
        return self.fabrica()


def _random_forest(parametros: dict) -> Candidato:
    return Candidato(
        'random_forest', 'Random Forest Regressor', parametros,
        lambda: RandomForestRegressor(n_estimators=300, random_state=SEMENTE, n_jobs=-1, **parametros),
    )


def candidatos() -> list[Candidato]:
    """Configuracoes avaliadas na validacao temporal dentro do treino."""
    grade_rf = [{'max_depth': profundidade, 'min_samples_leaf': folha}
                for profundidade in (None, 8) for folha in (1, 5)]
    return [Candidato('regressao_linear', 'Regressão Linear', {}, LinearRegression),
            *(_random_forest(p) for p in grade_rf)]


def referencia() -> Candidato:
    return Candidato('media_4_trimestres', 'Média dos 4 trimestres anteriores', {}, MediaUltimosQuatro)
