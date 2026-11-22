"""Serviços: regras de negócio (tendência, histórico mínimo, montagem da resposta)."""
from typing import Optional

import psycopg

from app import repositorio
from app.config import minimo_trimestres

LIMITE_TENDENCIA = 10.0  # percentual: > +10 crescente, < -10 decrescente
JANELA = 4

AVISO_ESTIMATIVA = (
    'Esta previsão é uma estimativa gerada por inteligência artificial a partir de dados '
    'históricos. Ela não garante a existência de vagas nem de emprego e não é uma '
    'recomendação profissional.'
)

INFORMACOES_USADAS = [
    {'chave': 'historico',
     'descricao': 'Quantidade de vagas da ocupação nos 4 trimestres anteriores ao previsto.'},
    {'chave': 'sazonalidade',
     'descricao': 'Trimestre do ano (1 a 4), para considerar épocas de mais ou menos contratação.'},
    {'chave': 'tendencia_recente',
     'descricao': 'Comportamento recente das vagas da ocupação, comparando trimestres próximos.'},
]


def rotulo_periodo(ano: int, trimestre: int) -> str:
    return f'{ano}-T{trimestre}'


def proximo_trimestre(ano: int, trimestre: int) -> tuple[int, int]:
    return (ano + 1, 1) if trimestre == 4 else (ano, trimestre + 1)


def calcular_tendencia(serie: list[dict], minimo: int) -> dict:
    """RF03: soma dos últimos 4 trimestres vs. os 4 anteriores.

    Usa os trimestres COM dados (lacunas não viram zero). Sem `minimo` trimestres,
    ou com base anterior zero, a tendência fica indisponível com explicação.
    """
    indisponivel = {
        'disponivel': False, 'classificacao': None, 'variacao_percentual': None,
        'soma_recente': None, 'soma_anterior': None,
        'periodo_recente': None, 'periodo_anterior': None, 'frase': None, 'motivo': None,
    }
    if len(serie) < max(minimo, 2 * JANELA):
        indisponivel['motivo'] = (
            f'Tendência indisponível: a ocupação tem {len(serie)} trimestre(s) com dados e '
            f'são necessários pelo menos {max(minimo, 2 * JANELA)} para comparar os últimos 4 '
            'trimestres com os 4 anteriores.'
        )
        return indisponivel
    recente = serie[-JANELA:]
    anterior = serie[-2 * JANELA:-JANELA]
    soma_r = sum(p['quantidade_vagas'] for p in recente)
    soma_a = sum(p['quantidade_vagas'] for p in anterior)
    periodos = {
        'periodo_recente': {'inicio': rotulo_periodo(recente[0]['ano'], recente[0]['trimestre']),
                            'fim': rotulo_periodo(recente[-1]['ano'], recente[-1]['trimestre'])},
        'periodo_anterior': {'inicio': rotulo_periodo(anterior[0]['ano'], anterior[0]['trimestre']),
                             'fim': rotulo_periodo(anterior[-1]['ano'], anterior[-1]['trimestre'])},
    }
    if soma_a == 0:
        indisponivel.update(periodos, soma_recente=soma_r, soma_anterior=soma_a, motivo=(
            'Tendência indisponível: não houve vagas nos 4 trimestres anteriores, '
            'então a variação percentual não pode ser calculada.'))
        return indisponivel
    variacao = 100.0 * (soma_r - soma_a) / soma_a
    if variacao > LIMITE_TENDENCIA:
        classe, descricao = 'crescente', 'estão crescendo'
    elif variacao < -LIMITE_TENDENCIA:
        classe, descricao = 'decrescente', 'estão diminuindo'
    else:
        classe, descricao = 'estável', 'estão estáveis'
    frase = (f'As vagas desta ocupação {descricao}: foram {soma_r} nos últimos 4 trimestres '
             f'com dados, contra {soma_a} nos 4 anteriores ({variacao:+.1f}%).')
    return {'disponivel': True, 'classificacao': classe, 'variacao_percentual': round(variacao, 1),
            'soma_recente': soma_r, 'soma_anterior': soma_a, **periodos, 'frase': frase,
            'motivo': None}


def buscar(conexao: psycopg.Connection, texto: str, limite: int) -> list[dict]:
    return repositorio.buscar_ocupacoes(conexao, texto, limite)


def detalhar_ocupacao(conexao: psycopg.Connection, ocupacao_id: int) -> Optional[dict]:
    ocupacao = repositorio.obter_ocupacao(conexao, ocupacao_id)
    if ocupacao is None:
        return None
    serie = repositorio.obter_serie(conexao, ocupacao_id)
    ocupacao['total_trimestres'] = len(serie)
    ocupacao['primeiro_periodo'] = rotulo_periodo(serie[0]['ano'], serie[0]['trimestre']) if serie else None
    ocupacao['ultimo_periodo'] = rotulo_periodo(serie[-1]['ano'], serie[-1]['trimestre']) if serie else None
    return ocupacao


def montar_serie(conexao: psycopg.Connection, ocupacao_id: int) -> Optional[dict]:
    """Histórico + tendência + contrato de previsão (A13 preenche a tabela `previsao`)."""
    ocupacao = repositorio.obter_ocupacao(conexao, ocupacao_id)
    if ocupacao is None:
        return None
    minimo = minimo_trimestres_config()
    serie = repositorio.obter_serie(conexao, ocupacao_id)
    suficiente = len(serie) >= minimo
    previsao, motivo = None, None
    if not suficiente:
        motivo = (f'Esta ocupação tem {len(serie)} trimestre(s) com dados e o mínimo para gerar '
                  f'previsão é {minimo}. Exibimos apenas o histórico disponível.')
    elif serie:
        ano, tri = proximo_trimestre(serie[-1]['ano'], serie[-1]['trimestre'])
        gravada = repositorio.obter_previsao(conexao, ocupacao_id, ano, tri)
        if gravada:
            previsao = {
                'trimestre_alvo': rotulo_periodo(gravada['ano_alvo'], gravada['trimestre_alvo']),
                'quantidade_estimada': float(gravada['quantidade_prevista']),
                'algoritmo': gravada['algoritmo'],
            }
        else:
            motivo = (f'A previsão para {rotulo_periodo(ano, tri)} ainda não foi gerada '
                      'para esta ocupação.')
    return {
        'ocupacao': ocupacao,
        'total_trimestres': len(serie),
        'serie': [{'periodo': rotulo_periodo(p['ano'], p['trimestre']), 'ano': p['ano'],
                   'trimestre': p['trimestre'], 'quantidade_vagas': p['quantidade_vagas']}
                  for p in serie],
        'tendencia': calcular_tendencia(serie, minimo),
        'historico_suficiente': suficiente,
        'minimo_trimestres': minimo,
        'previsao': previsao,
        'motivo_sem_previsao': motivo,
        'aviso': AVISO_ESTIMATIVA,
        'informacoes_usadas': INFORMACOES_USADAS if previsao else [],
    }


def minimo_trimestres_config() -> int:
    return minimo_trimestres()
