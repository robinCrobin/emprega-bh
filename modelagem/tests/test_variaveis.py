import unittest

import pandas as pd

from modelagem.dados import indice_trimestre, rotulo
from modelagem.variaveis import (VARIAVEIS, avaliar_elegibilidade, divisao_temporal, linha_variaveis,
                                 minimo_trimestres, montar_entrada_previsao, montar_exemplos)

INICIO = indice_trimestre(2021, 1)


def dados(series: dict[str, list[int | None]]) -> pd.DataFrame:
    linhas = [{'codigo_cbo': cbo, 'nome_padronizado': f'Ocupacao {cbo}', 'indice': INICIO + i, 'vagas': v}
              for cbo, valores in series.items() for i, v in enumerate(valores) if v is not None]
    return pd.DataFrame(linhas).sort_values(['codigo_cbo', 'indice']).reset_index(drop=True)


class ElegibilidadeTests(unittest.TestCase):
    """A12: regra minima de oito trimestres, avaliada antes do alvo."""

    def test_sete_trimestres_nao_gera_previsao(self):
        ok, motivo = avaliar_elegibilidade(set(range(INICIO, INICIO + 7)), INICIO + 7, 8)
        self.assertFalse(ok)
        self.assertIn('7 trimestre(s)', motivo)
        self.assertIn('minimo para gerar previsao e 8', motivo)

    def test_oito_trimestres_gera_previsao(self):
        self.assertEqual(avaliar_elegibilidade(set(range(INICIO, INICIO + 8)), INICIO + 8, 8), (True, None))

    def test_lacuna_nos_quatro_anteriores_impede_previsao(self):
        indices = set(range(INICIO, INICIO + 10)) - {INICIO + 8}
        ok, motivo = avaliar_elegibilidade(indices, INICIO + 10, 8)
        self.assertFalse(ok)
        self.assertIn(rotulo(INICIO + 8), motivo)
        self.assertIn('nao sao tratadas como zero', motivo)

    def test_trimestres_posteriores_ao_alvo_nao_contam(self):
        indices = set(range(INICIO, INICIO + 20))
        self.assertFalse(avaliar_elegibilidade(indices, INICIO + 6, 8)[0])

    def test_minimo_configuravel_nunca_abaixo_da_janela(self):
        self.assertEqual(minimo_trimestres(12), 12)
        self.assertEqual(minimo_trimestres(2), 4)
        self.assertEqual(minimo_trimestres('x'), 8)


class VariaveisTests(unittest.TestCase):
    """A10: ultimos quatro trimestres e trimestre do ano."""

    def test_defasagens_e_trimestre_do_ano(self):
        serie = {INICIO + i: 10 * (i + 1) for i in range(8)}
        alvo = INICIO + 6  # 2022-T3
        linha = linha_variaveis(serie, alvo)
        self.assertEqual([linha[f'defasagem_{k}'] for k in range(1, 5)], [60, 50, 40, 30])
        self.assertEqual((linha['trimestre_2'], linha['trimestre_3'], linha['trimestre_4']), (0, 1, 0))
        self.assertEqual(list(linha), VARIAVEIS)

    def test_exemplos_sem_vazamento_nem_zero_inventado(self):
        exemplos = montar_exemplos(dados({'111111': list(range(1, 13))}), 8)
        self.assertEqual(exemplos['periodo_alvo'].tolist(), ['2023-T1', '2023-T2', '2023-T3', '2023-T4'])
        for linha in exemplos.itertuples():
            self.assertEqual(linha.defasagem_1, linha.vagas - 1)  # so valores anteriores ao alvo

    def test_lacuna_exclui_exemplos_que_dependem_dela(self):
        valores = list(range(1, 17))
        valores[9] = None  # 2023-T2 ausente: alvos 2023-T2 a 2024-T2 dependem dele
        exemplos = montar_exemplos(dados({'111111': valores}), 8)
        self.assertEqual(exemplos['periodo_alvo'].tolist(), ['2023-T1', '2024-T3', '2024-T4'])
        self.assertNotIn(0, exemplos[VARIAVEIS[:4]].to_numpy())

    def test_entrada_previsao_so_para_series_ate_o_ultimo_trimestre(self):
        base = dados({'111111': [5] * 10, '222222': [5] * 7 + [None] * 3,
                      '333333': [5] * 7, '444444': [None] * 3 + [5] * 7, '555555': [5] * 9 + [None]})
        alvo = INICIO + 10
        elegiveis, sem = montar_entrada_previsao(base, alvo, 8)
        self.assertEqual(elegiveis['codigo_cbo'].tolist(), ['111111'])
        motivos = dict(zip(sem['codigo_cbo'], sem['motivo']))
        self.assertIn('Historico insuficiente: 7', motivos['333333'])
        self.assertIn('Historico insuficiente: 7', motivos['444444'])
        self.assertIn('Historico insuficiente: 7', motivos['222222'])
        self.assertIn('Sem dados em 2023-T2', motivos['555555'])  # serie parou antes do alvo


class DivisaoTemporalTests(unittest.TestCase):
    def test_treino_inteiramente_anterior_ao_teste(self):
        exemplos = montar_exemplos(dados({'111111': list(range(1, 21)), '222222': list(range(5, 25))}), 8)
        divisao = divisao_temporal(exemplos, 4)
        self.assertLess(divisao.treino['alvo_indice'].max(), divisao.teste['alvo_indice'].min())
        self.assertEqual(divisao.periodos_teste, ('2025-T1', '2025-T4'))
        self.assertEqual(divisao.periodos_treino, ('2023-T1', '2024-T4'))
        self.assertEqual(len(divisao.treino) + len(divisao.teste), len(exemplos))

    def test_poucos_trimestres_para_teste(self):
        exemplos = montar_exemplos(dados({'111111': list(range(1, 12))}), 8)
        with self.assertRaises(ValueError):
            divisao_temporal(exemplos, 4)


if __name__ == '__main__':
    unittest.main()
