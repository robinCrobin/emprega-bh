"""Testes unitários da regra de negócio (sem banco): tendência e histórico mínimo."""
import pytest

from app.banco.normalizacao import normalizar_texto
from app.servicos import calcular_tendencia, proximo_trimestre


def serie(vagas):
    return [{'ano': 2021 + i // 4, 'trimestre': i % 4 + 1, 'quantidade_vagas': v}
            for i, v in enumerate(vagas)]


def test_tendencia_crescente():
    t = calcular_tendencia(serie([10] * 4 + [12] * 4), 8)  # +20%
    assert t['disponivel'] and t['classificacao'] == 'crescente'
    assert t['variacao_percentual'] == 20.0 and (t['soma_recente'], t['soma_anterior']) == (48, 40)
    assert t['periodo_recente'] == {'inicio': '2022-T1', 'fim': '2022-T4'}


def test_tendencia_decrescente():
    assert calcular_tendencia(serie([10] * 4 + [8] * 4), 8)['classificacao'] == 'decrescente'


def test_tendencia_estavel_inclusive_nos_limites_exatos():
    assert calcular_tendencia(serie([10] * 4 + [11] * 4), 8)['classificacao'] == 'estável'  # +10%
    assert calcular_tendencia(serie([10] * 4 + [9] * 4), 8)['classificacao'] == 'estável'   # -10%
    assert calcular_tendencia(serie([10] * 4 + [10] * 4), 8)['classificacao'] == 'estável'


def test_tendencia_logo_acima_do_limite():
    assert calcular_tendencia(serie([100] * 4 + [111] * 4), 8)['classificacao'] == 'crescente'


def test_tendencia_usa_apenas_os_ultimos_oito_trimestres():
    t = calcular_tendencia(serie([999] * 5 + [10] * 4 + [20] * 4), 8)
    assert (t['soma_anterior'], t['soma_recente']) == (40, 80)


def test_tendencia_indisponivel_com_dados_insuficientes():
    t = calcular_tendencia(serie([1] * 7), 8)
    assert t['disponivel'] is False and t['classificacao'] is None and '7' in t['motivo']


def test_tendencia_indisponivel_quando_base_anterior_zero():
    t = calcular_tendencia(serie([0] * 4 + [5] * 4), 8)
    assert t['disponivel'] is False and 'anteriores' in t['motivo']


def test_proximo_trimestre():
    assert proximo_trimestre(2026, 4) == (2027, 1)
    assert proximo_trimestre(2026, 2) == (2026, 3)


@pytest.mark.parametrize('texto', ['  Técnico em ENFERMAGEM ', 'tecnico   em enfermagem', 'Técnico-em-Enfermagem'])
def test_normalizacao_ignora_acento_caixa_e_pontuacao(texto):
    assert normalizar_texto(texto) == 'tecnico em enfermagem'
