import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from modelagem.dados import (ErroDados, carregar_vagas, data_referencia_da_coleta, indice_trimestre,
                             remover_trimestres_abertos, rotulo, ultimo_trimestre_fechado)
from modelagem.tests.auxiliares import escrever_csv, serie


class TrimestreFechadoTests(unittest.TestCase):
    def test_trimestre_em_andamento_nao_e_fechado(self):
        self.assertEqual(rotulo(ultimo_trimestre_fechado(date(2026, 11, 27))), '2026-T3')
        self.assertEqual(rotulo(ultimo_trimestre_fechado(date(2026, 12, 31))), '2026-T3')

    def test_virada_de_ano(self):
        self.assertEqual(rotulo(ultimo_trimestre_fechado(date(2027, 1, 1))), '2026-T4')

    def test_indices_consecutivos(self):
        self.assertEqual(indice_trimestre(2022, 1) - indice_trimestre(2021, 4), 1)

    def test_data_da_coleta_no_manifesto(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'm.json'
            caminho.write_text(json.dumps({'collected_at': '2026-11-20T10:00:00-03:00'}), encoding='utf-8')
            self.assertEqual(data_referencia_da_coleta(caminho), date(2026, 11, 20))
            self.assertIsNone(data_referencia_da_coleta(Path(pasta) / 'ausente.json'))


class CarregarVagasTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.caminho = Path(self.pasta.name) / 'vagas.csv'

    def test_preserva_zero_a_esquerda_e_ordena(self):
        escrever_csv(self.caminho, serie('Ocupacao A', '012345', [3, 5])[::-1])
        dados, _ = carregar_vagas(self.caminho)
        self.assertEqual(dados['codigo_cbo'].tolist(), ['012345', '012345'])
        self.assertEqual(dados['vagas'].tolist(), [3, 5])

    def test_soma_nomes_diferentes_do_mesmo_cbo_no_trimestre(self):
        escrever_csv(self.caminho, serie('Balconista', '521140', [2, 1]) + serie('Atendente', '521140', [10]))
        dados, resumo = carregar_vagas(self.caminho)
        self.assertEqual(dados['vagas'].tolist(), [12, 1])
        self.assertEqual(set(dados['nome_padronizado']), {'Atendente'})  # nome com mais vagas
        self.assertEqual((resumo.linhas_consolidadas, resumo.cbos_com_varios_nomes), (1, 1))

    def test_descarta_cbo_invalido_ausente_ou_nao_validado(self):
        linhas = (serie('Valida', '111111', [1]) + serie('Dupla', '765240;991310', [1])
                  + serie('Sem', '', [1]) + [{**serie('Pend', '222222', [1])[0], 'status_validacao': 'pendente'}])
        escrever_csv(self.caminho, linhas)
        dados, resumo = carregar_vagas(self.caminho)
        self.assertEqual(dados['codigo_cbo'].tolist(), ['111111'])
        self.assertEqual((resumo.linhas_cbo_invalido, resumo.linhas_sem_cbo, resumo.linhas_nao_validadas),
                         (1, 1, 1))

    def test_rejeita_trimestre_mal_formatado(self):
        escrever_csv(self.caminho, [{'nome_padronizado': 'A', 'codigo_cbo': '111111',
                                     'quarter': '2021-Q1', 'vacancies': 1}])
        with self.assertRaises(ErroDados):
            carregar_vagas(self.caminho)

    def test_rejeita_vagas_negativas_ou_texto(self):
        for valor in (-1, 'abc', 1.5):
            escrever_csv(self.caminho, serie('A', '111111', [valor]))
            with self.assertRaises(ErroDados, msg=valor):
                carregar_vagas(self.caminho)

    def test_rejeita_coluna_ausente(self):
        self.caminho.write_text('codigo_cbo,quarter\n111111,2021-T1\n', encoding='utf-8')
        with self.assertRaises(ErroDados):
            carregar_vagas(self.caminho)

    def test_remove_trimestres_abertos(self):
        escrever_csv(self.caminho, serie('A', '111111', [1, 2, 3]))
        dados, resumo = carregar_vagas(self.caminho)
        restante = remover_trimestres_abertos(dados, indice_trimestre(2021, 2), resumo)
        self.assertEqual(len(restante), 2)
        self.assertEqual(resumo.trimestres_abertos, ['2021-T3'])


if __name__ == '__main__':
    unittest.main()
