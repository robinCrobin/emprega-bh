"""Gravacao no PostgreSQL em schema isolado; ignorado se o banco nao estiver ativo."""
import unittest
import uuid

import pandas as pd
import psycopg

from modelagem.banco import gravar, opcoes_conexao
from modelagem.dados import RAIZ

MIGRACAO = RAIZ / 'database' / 'migrations' / '001_esquema_inicial.sql'


def manifesto(alvo='2026-T4'):
    return {
        'gerado_em': '2026-11-27T00:00:00-03:00', 'dados': {'sha256': 'a' * 64},
        'divisao_temporal': {'teste': {'periodo': ['2025-T4', '2026-T3']}},
        'selecao': {'familia': 'random_forest'},
        'teste': {
            'regressao_linear': {'algoritmo': 'Regressão Linear', 'candidato': 'regressao_linear',
                                 'mae': 2.5, 'rmse': 3.5, 'exemplos': 10},
            'random_forest': {'algoritmo': 'Random Forest Regressor', 'candidato': 'random_forest(x=1)',
                              'mae': 1.5, 'rmse': 2.5, 'exemplos': 10},
        },
        'previsoes': {'trimestre_alvo': alvo},
    }


def previsoes(cbos_e_valores):
    return pd.DataFrame([{'codigo_cbo': c, 'ano_alvo': 2026, 'trimestre_alvo': 4, 'quantidade_prevista': v,
                          'algoritmo': 'random_forest'} for c, v in cbos_e_valores])


class GravarBancoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.admin = psycopg.connect(**{**opcoes_conexao(), 'connect_timeout': 2}, autocommit=True)
        except psycopg.OperationalError as erro:
            raise unittest.SkipTest(f'PostgreSQL indisponivel: {type(erro).__name__}')
        cls.schema = f'teste_modelo_{uuid.uuid4().hex[:8]}'
        cls.admin.execute(f'CREATE SCHEMA {cls.schema}')
        cls.conexao = psycopg.connect(**opcoes_conexao(), options=f'-c search_path={cls.schema},public')
        cls.conexao.execute(MIGRACAO.read_text(encoding='utf-8'))
        cls.conexao.commit()

    @classmethod
    def tearDownClass(cls):
        cls.conexao.close()
        cls.admin.execute(f'DROP SCHEMA {cls.schema} CASCADE')
        cls.admin.close()

    def setUp(self):
        self.conexao.execute('TRUNCATE ocupacao, metrica_modelo RESTART IDENTITY CASCADE')
        for cbo in ('999001', '999002'):
            self.conexao.execute('INSERT INTO ocupacao (codigo_cbo, nome, nome_normalizado) VALUES (%s, %s, %s)',
                                 (cbo, f'Ficticia {cbo}', f'ficticia {cbo}'))
        self.conexao.commit()

    def consultar(self, sql):
        return self.conexao.execute(sql).fetchall()

    def test_grava_metricas_e_previsoes_por_cbo(self):
        resumo = gravar(self.conexao, manifesto(), previsoes([('999001', 12.34), ('999002', 0), ('123456', 5)]))
        self.assertEqual((resumo.metricas, resumo.previsoes), (2, 2))
        self.assertEqual(resumo.cbos_sem_ocupacao, ['123456'])
        linhas = self.consultar('SELECT o.codigo_cbo, p.ano_alvo, p.trimestre_alvo, p.quantidade_prevista::float, '
                                'p.algoritmo FROM previsao p JOIN ocupacao o ON o.id = p.ocupacao_id ORDER BY 1')
        self.assertEqual(linhas, [('999001', 2026, 4, 12.34, 'random_forest'),
                                  ('999002', 2026, 4, 0.0, 'random_forest')])
        metricas = self.consultar('SELECT algoritmo, mae::float, rmse::float FROM metrica_modelo ORDER BY id')
        self.assertEqual(metricas, [('regressao_linear', 2.5, 3.5), ('random_forest', 1.5, 2.5)])

    def test_reexecucao_atualiza_e_remove_previsao_que_deixou_de_valer(self):
        gravar(self.conexao, manifesto(), previsoes([('999001', 10), ('999002', 20)]))
        resumo = gravar(self.conexao, manifesto(), previsoes([('999001', 11)]))
        self.assertEqual(resumo.previsoes_removidas, 1)
        self.assertEqual(self.consultar('SELECT quantidade_prevista::float FROM previsao'), [(11.0,)])


if __name__ == '__main__':
    unittest.main()
