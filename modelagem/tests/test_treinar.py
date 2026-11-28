"""Execucao completa com dados FICTICIOS: artefatos, regra minima e reprodutibilidade."""
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from modelagem.treinar import Configuracao, executar, main
from modelagem.variaveis import VARIAVEIS
from modelagem.tests.auxiliares import escrever_csv, periodo, serie


def base_ficticia() -> list[dict]:
    linhas = []
    for o in range(10):  # 20 trimestres (2021-T1 a 2025-T4) com sazonalidade
        valores = [round((5 + 3 * o) * (1 + 0.3 * math.sin(i)) + i) for i in range(20)]
        linhas += serie(f'Ocupacao {o}', f'90{o:04d}', valores)
    linhas += serie('Sete trimestres', '800001', [4] * 7, inicio=13)       # 2024-T2 a 2025-T4
    linhas += serie('Parou antes', '800002', [6] * 12)                      # termina em 2023-T4
    linhas += serie('Lacuna recente', '800003', [3] * 17 + [None, 3, 3])   # falta 2025-T2
    linhas += [{'nome_padronizado': 'Ocupacao 0', 'codigo_cbo': '900000', 'quarter': periodo(20),
                'vacancies': 1}]                                             # 2026-T1 em andamento
    return linhas


class TreinarTests(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)
        self.csv = escrever_csv(self.raiz / 'vagas.csv', base_ficticia())

    def config(self, subpasta: str) -> Configuracao:
        saida = self.raiz / subpasta
        return Configuracao(dados=self.csv, manifesto_coleta=self.raiz / 'sem_manifesto.json',
                            data_referencia=date(2026, 2, 10), minimo_trimestres=8,
                            pasta_modelos=saida / 'models', pasta_relatorios=saida / 'reports',
                            arquivo_previsoes=saida / 'previsoes.csv')

    def test_execucao_completa(self):
        m = executar(self.config('a'))
        self.assertEqual(m['dados']['trimestres_abertos_descartados'], ['2026-T1'])
        self.assertEqual(m['divisao_temporal']['teste']['periodo'], ['2025-T1', '2025-T4'])
        self.assertEqual(m['divisao_temporal']['treino']['periodo'][1], '2024-T4')
        self.assertEqual(set(m['teste']), {'regressao_linear', 'random_forest', 'media_4_trimestres'})
        for r in m['teste'].values():
            self.assertGreaterEqual(r['mae'], 0)
            self.assertGreaterEqual(r['rmse'], r['mae'])
        self.assertIn(m['selecao']['familia'], {'regressao_linear', 'random_forest'})

        previsoes = pd.read_csv(self.raiz / 'a' / 'previsoes.csv', dtype={'codigo_cbo': str})
        self.assertEqual(set(previsoes['periodo_alvo']), {'2026-T1'})
        self.assertEqual(sorted(previsoes['codigo_cbo']), [f'90{o:04d}' for o in range(10)])
        self.assertTrue((previsoes['quantidade_prevista'] >= 0).all())
        self.assertTrue((previsoes['trimestres_historico'] >= 8).all())
        self.assertEqual(set(previsoes['algoritmo']), {m['selecao']['familia']})
        self.assertIn('mae', m['escolhido_supera_referencia_na_validacao'])

        sem = pd.read_csv(self.raiz / 'a' / 'reports' / 'ocupacoes_sem_previsao.csv', dtype={'codigo_cbo': str})
        self.assertEqual(sorted(sem['codigo_cbo']), ['800001', '800002', '800003'])

        artefato = joblib.load(self.raiz / 'a' / 'models' / 'modelo_vagas.joblib')
        self.assertEqual(artefato['variaveis'], VARIAVEIS)
        self.assertEqual(artefato['minimo_trimestres'], 8)
        manifesto = json.loads((self.raiz / 'a' / 'models' / 'manifesto_modelo.json').read_text(encoding='utf-8'))
        self.assertEqual(manifesto['semente'], 42)
        self.assertTrue((self.raiz / 'a' / 'reports' / 'avaliacao_modelo.md').exists())

    def test_reprodutivel_com_a_mesma_semente(self):
        executar(self.config('a'))
        executar(self.config('b'))
        a = (self.raiz / 'a' / 'previsoes.csv').read_text(encoding='utf-8')
        b = (self.raiz / 'b' / 'previsoes.csv').read_text(encoding='utf-8')
        self.assertEqual(a, b)

    def test_cli_falha_sem_arquivo(self):
        self.assertEqual(main(['--dados', str(self.raiz / 'nao_existe.csv')]), 1)


if __name__ == '__main__':
    unittest.main()
