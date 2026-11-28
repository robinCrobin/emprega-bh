import math
import unittest

import numpy as np
import pandas as pd

from modelagem.avaliacao import melhor, metricas, prever, validacao_expansiva
from modelagem.modelos import SEMENTE, MediaUltimosQuatro, candidatos
from modelagem.modelos import Candidato
from modelagem.variaveis import ALVO, VARIAVEIS


def exemplos_ficticios(trimestres: int = 10, por_trimestre: int = 3) -> pd.DataFrame:
    linhas = []
    for q in range(trimestres):
        for o in range(por_trimestre):
            linha = {v: o + q for v in VARIAVEIS}
            linhas.append({'codigo_cbo': f'{o:06d}', 'alvo_indice': 8100 + q, **linha, ALVO: float(8100 + q)})
    return pd.DataFrame(linhas)


class Espiao:
    """Registra os alvos vistos no ajuste; o alvo codifica o trimestre."""

    def __init__(self, registro):
        self.registro = registro

    def fit(self, X, y):
        self.registro.append(set(y.tolist()))
        return self

    def predict(self, X):
        return np.zeros(len(X))


class MetricasTests(unittest.TestCase):
    def test_mae_e_rmse(self):
        r = metricas([0, 10], [2, 6])
        self.assertAlmostEqual(r['mae'], 3.0)
        self.assertAlmostEqual(r['rmse'], math.sqrt(10))
        self.assertEqual(r['exemplos'], 2)

    def test_previsao_nunca_negativa(self):
        class Negativo:
            def predict(self, X):
                return np.full(len(X), -5.0)
        self.assertTrue((prever(Negativo(), exemplos_ficticios(1)) == 0).all())

    def test_referencia_e_media_dos_quatro_anteriores(self):
        linha = {v: 0 for v in VARIAVEIS}
        linha.update(defasagem_1=4, defasagem_2=8, defasagem_3=12, defasagem_4=16, trimestre_3=1)
        X = pd.DataFrame([linha])[VARIAVEIS].to_numpy(dtype=float)
        self.assertEqual(MediaUltimosQuatro().fit(X).predict(X).tolist(), [10.0])


class ValidacaoTemporalTests(unittest.TestCase):
    def test_cada_dobra_ajusta_somente_com_o_passado(self):
        registro = []
        candidato = Candidato('espiao', 'Espiao', {}, lambda: Espiao(registro))
        resultado = validacao_expansiva(candidato, exemplos_ficticios(10), dobras=4)
        self.assertEqual([d['periodo_validacao'] for d in resultado['dobras']],
                         ['2026-T3', '2026-T4', '2027-T1', '2027-T2'])
        for dobra, alvos_ajuste in zip(resultado['dobras'], registro):
            ano, tri = map(int, dobra['periodo_validacao'].split('-T'))
            self.assertLess(max(alvos_ajuste), ano * 4 + tri - 1)
        self.assertEqual(resultado['exemplos'], 12)

    def test_dobras_demais(self):
        with self.assertRaises(ValueError):
            validacao_expansiva(candidatos()[0], exemplos_ficticios(4), dobras=4)

    def test_melhor_por_mae_com_desempate_por_rmse(self):
        resultados = [{'mae': 2.0, 'rmse': 5.0, 'id': 'a'}, {'mae': 1.0, 'rmse': 9.0, 'id': 'b'},
                      {'mae': 1.0, 'rmse': 3.0, 'id': 'c'}]
        self.assertEqual(melhor(resultados)['id'], 'c')


class CandidatosTests(unittest.TestCase):
    def test_compara_regressao_linear_e_random_forest_com_semente(self):
        lista = candidatos()
        self.assertEqual({c.familia for c in lista}, {'regressao_linear', 'random_forest'})
        for c in lista:
            if c.familia == 'random_forest':
                self.assertEqual(c.criar().random_state, SEMENTE)
        self.assertEqual(len({c.chave for c in lista}), len(lista))


if __name__ == '__main__':
    unittest.main()
