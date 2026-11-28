"""Gravacao opcional dos resultados do modelo no PostgreSQL.

- metrica_modelo: MAE/RMSE do teste reservado (uma linha por algoritmo avaliado).
  `algoritmo` usa o identificador estavel (regressao_linear, random_forest,
  media_4_trimestres), como no exemplo de docs/API_CONTRATO.md.
- previsao: estimativas do proximo trimestre, ligadas a ocupacao pelo codigo_cbo.

A API so le essas tabelas (docs/DADOS_E_INTEGRACAO.md). A integracao com a API
e responsabilidade da A13; este comando e o ponto de entrega do modelo.

Uso, na raiz, depois de `python -m app.banco.cli migrar` e da carga do historico:
    python -m modelagem.banco
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

from modelagem.dados import RAIZ

MANIFESTO_PADRAO = RAIZ / 'models' / 'manifesto_modelo.json'
PREVISOES_PADRAO = RAIZ / 'data' / 'processed' / 'previsoes_proximo_trimestre.csv'


def opcoes_conexao() -> dict:
    """Mesmas variaveis da API (backend/app/config.py)."""
    load_dotenv(RAIZ / '.env', override=False)
    return {
        'host': os.getenv('PGHOST', '127.0.0.1'),
        'port': int(os.getenv('PGPORT', os.getenv('DB_PORT', '5433'))),
        'dbname': os.getenv('POSTGRES_DB', 'empregabh'),
        'user': os.getenv('POSTGRES_USER', 'empregabh'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
        'connect_timeout': 5,
    }


@dataclass
class ResumoGravacao:
    metricas: int
    previsoes: int
    previsoes_removidas: int
    cbos_sem_ocupacao: list[str]


def gravar(conexao: psycopg.Connection, manifesto: dict, previsoes: pd.DataFrame) -> ResumoGravacao:
    """Grava metricas e previsoes numa unica transacao.

    Para o trimestre alvo, previsoes de ocupacoes que deixaram de ser elegiveis
    sao removidas, evitando exibir estimativa de uma execucao anterior.
    """
    teste = manifesto['divisao_temporal']['teste']
    escolhido = manifesto['selecao']['familia']
    with conexao.transaction(), conexao.cursor() as cur:
        for familia, r in manifesto['teste'].items():
            observacoes = (f'teste {teste["periodo"][0]} a {teste["periodo"][1]}; n={r["exemplos"]}; '
                           f'config={r["candidato"]}; escolhido={"sim" if familia == escolhido else "nao"}; '
                           f'dados sha256={manifesto["dados"]["sha256"][:12]}; '
                           f'manifesto={manifesto["gerado_em"]}')
            cur.execute('INSERT INTO metrica_modelo (algoritmo, mae, rmse, observacoes) VALUES (%s, %s, %s, %s)',
                        (familia, r['mae'], r['rmse'], observacoes))

        cbos = previsoes['codigo_cbo'].astype(str).tolist()
        cur.execute('SELECT codigo_cbo, id FROM ocupacao WHERE codigo_cbo = ANY(%s)', (cbos,))
        ids = dict(cur.fetchall())
        ausentes = sorted(set(cbos) - set(ids))
        gravadas = []
        for linha in previsoes.itertuples(index=False):
            oid = ids.get(str(linha.codigo_cbo))
            if oid is None:
                continue
            cur.execute(
                'INSERT INTO previsao (ocupacao_id, ano_alvo, trimestre_alvo, quantidade_prevista, algoritmo) '
                'VALUES (%s, %s, %s, %s, %s) '
                'ON CONFLICT (ocupacao_id, ano_alvo, trimestre_alvo) DO UPDATE SET '
                'quantidade_prevista = EXCLUDED.quantidade_prevista, algoritmo = EXCLUDED.algoritmo, '
                'gerado_em = now()',
                (oid, int(linha.ano_alvo), int(linha.trimestre_alvo), float(linha.quantidade_prevista),
                 linha.algoritmo))
            gravadas.append(oid)

        ano, trimestre = (int(v) for v in manifesto['previsoes']['trimestre_alvo'].split('-T'))
        cur.execute('DELETE FROM previsao WHERE ano_alvo = %s AND trimestre_alvo = %s '
                    'AND NOT (ocupacao_id = ANY(%s))', (ano, trimestre, gravadas))
        removidas = cur.rowcount
    return ResumoGravacao(len(manifesto['teste']), len(gravadas), removidas, ausentes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Grava metricas e previsoes do modelo no PostgreSQL.')
    parser.add_argument('--manifesto', type=Path, default=MANIFESTO_PADRAO)
    parser.add_argument('--previsoes', type=Path, default=PREVISOES_PADRAO)
    args = parser.parse_args(argv)
    for arquivo in (args.manifesto, args.previsoes):
        if not arquivo.exists():
            print(f'Arquivo nao encontrado: {arquivo}. Execute python -m modelagem.treinar.', file=sys.stderr)
            return 1
    manifesto = json.loads(args.manifesto.read_text(encoding='utf-8'))
    previsoes = pd.read_csv(args.previsoes, dtype={'codigo_cbo': str})
    try:
        with psycopg.connect(**opcoes_conexao()) as conexao:
            resumo = gravar(conexao, manifesto, previsoes)
    except psycopg.Error as erro:
        print(f'Erro de banco: {type(erro).__name__}. Verifique o .env, o PostgreSQL e as migracoes.',
              file=sys.stderr)
        return 1
    print(f'Gravadas {resumo.metricas} metricas e {resumo.previsoes} previsoes '
          f'({resumo.previsoes_removidas} antigas removidas do mesmo trimestre).')
    if resumo.cbos_sem_ocupacao:
        print(f'{len(resumo.cbos_sem_ocupacao)} CBO(s) sem ocupacao no banco (carregar o historico antes): '
              f'{", ".join(resumo.cbos_sem_ocupacao[:10])}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
