"""Modelos Pydantic de resposta (contrato público da API)."""
from typing import Optional

from pydantic import BaseModel, Field


class OcupacaoResumo(BaseModel):
    id: int = Field(description='Identificador da ocupação usado nas rotas.', examples=[1])
    nome: str = Field(description='Nome padronizado da ocupação.', examples=['Analista de sistemas'])
    codigo_cbo: Optional[str] = Field(description='Código CBO (6 dígitos), se disponível.', examples=['999101'])


class BuscaOcupacoes(BaseModel):
    termo: str = Field(description='Termo recebido na busca.')
    total_retornado: int = Field(description='Quantidade de resultados desta resposta (limitada por `limit`).')
    resultados: list[OcupacaoResumo]


class OcupacaoDetalhe(OcupacaoResumo):
    total_trimestres: int = Field(description='Trimestres com dados históricos.')
    primeiro_periodo: Optional[str] = Field(description='Primeiro trimestre com dados (AAAA-TN).', examples=['2021-T1'])
    ultimo_periodo: Optional[str] = Field(description='Último trimestre com dados (AAAA-TN).', examples=['2026-T4'])


class PontoSerie(BaseModel):
    periodo: str = Field(description='Rótulo do trimestre (AAAA-TN).', examples=['2024-T1'])
    ano: int
    trimestre: int = Field(ge=1, le=4)
    quantidade_vagas: int = Field(ge=0, description='Total de vagas ofertadas no trimestre.')


class Janela(BaseModel):
    inicio: str
    fim: str


class Tendencia(BaseModel):
    disponivel: bool
    classificacao: Optional[str] = Field(description='`crescente`, `decrescente` ou `estável`; nulo se indisponível.')
    variacao_percentual: Optional[float] = Field(description='Variação % (últimos 4 trimestres vs. 4 anteriores).')
    soma_recente: Optional[int]
    soma_anterior: Optional[int]
    periodo_recente: Optional[Janela]
    periodo_anterior: Optional[Janela]
    frase: Optional[str] = Field(description='Explicação em linguagem simples.')
    motivo: Optional[str] = Field(description='Por que a tendência não está disponível.')


class Previsao(BaseModel):
    trimestre_alvo: str = Field(description='Trimestre a que a previsão se refere (AAAA-TN).', examples=['2027-T1'])
    quantidade_estimada: float
    algoritmo: str


class InformacaoUsada(BaseModel):
    chave: str = Field(description='`historico`, `sazonalidade` ou `tendencia_recente`.')
    descricao: str


class SerieOcupacao(BaseModel):
    ocupacao: OcupacaoResumo
    total_trimestres: int
    serie: list[PontoSerie] = Field(description='Ordem cronológica, desde o início da base.')
    tendencia: Tendencia
    historico_suficiente: bool
    minimo_trimestres: int
    previsao: Optional[Previsao] = Field(description='Nulo sem histórico suficiente ou sem previsão gravada.')
    motivo_sem_previsao: Optional[str]
    aviso: str = Field(description='Aviso padronizado de estimativa (RF06).')
    informacoes_usadas: list[InformacaoUsada] = Field(description='O que embasou a previsão (RNF08); vazio sem previsão.')


class Erro(BaseModel):
    detail: str
