"""Rotas de ocupações e séries históricas."""
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app import servicos
from app.config import database_options, limite_maximo_busca
from app.schemas import BuscaOcupacoes, Erro, OcupacaoDetalhe, SerieOcupacao

router = APIRouter(prefix='/ocupacoes', tags=['Ocupações'])


def obter_conexao():
    """Uma conexão por requisição (dependência substituível nos testes)."""
    with psycopg.connect(**database_options()) as conexao:
        yield conexao


Conexao = Annotated[psycopg.Connection, Depends(obter_conexao)]
IdOcupacao = Annotated[int, Path(ge=1, le=2**62, description='Identificador da ocupação.')]
NAO_ENCONTRADA = {404: {'model': Erro, 'description': 'Ocupação não encontrada.'}}


@router.get('', response_model=BuscaOcupacoes, summary='Buscar ocupações pelo nome (RF01)')
def buscar_ocupacoes(
    conexao: Conexao,
    q: Annotated[str, Query(min_length=2, max_length=100,
                            description='Trecho do nome; ignora acentos e maiúsculas/minúsculas.')],
    limit: Annotated[int, Query(ge=1, description='Máximo de resultados (limitado pelo servidor).')] = 20,
):
    limite = min(limit, limite_maximo_busca())
    resultados = servicos.buscar(conexao, q, limite)
    return {'termo': q, 'total_retornado': len(resultados), 'resultados': resultados}


@router.get('/{ocupacao_id}', response_model=OcupacaoDetalhe, responses=NAO_ENCONTRADA,
            summary='Dados da ocupação e quantidade de trimestres com histórico')
def detalhar(conexao: Conexao, ocupacao_id: IdOcupacao):
    ocupacao = servicos.detalhar_ocupacao(conexao, ocupacao_id)
    if ocupacao is None:
        raise HTTPException(status_code=404, detail='Ocupação não encontrada.')
    return ocupacao


@router.get('/{ocupacao_id}/serie', response_model=SerieOcupacao, responses=NAO_ENCONTRADA,
            summary='Série histórica, tendência recente e contrato de previsão (RF02, RF03, RF04, RF05)')
def serie(conexao: Conexao, ocupacao_id: IdOcupacao):
    resposta = servicos.montar_serie(conexao, ocupacao_id)
    if resposta is None:
        raise HTTPException(status_code=404, detail='Ocupação não encontrada.')
    return resposta
