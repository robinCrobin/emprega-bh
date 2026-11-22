"""Aplicação dos scripts SQL versionados em database/migrations."""
from pathlib import Path

import psycopg

PASTA_MIGRACOES = Path(__file__).resolve().parents[3] / 'database' / 'migrations'


def aplicar_migracoes(conexao: psycopg.Connection, pasta: Path = PASTA_MIGRACOES) -> list[str]:
    """Executa em ordem os .sql ainda não registrados. Retorna os aplicados.

    Os scripts são idempotentes; o registro em schema_migracoes evita reaplicar.
    """
    arquivos = sorted(pasta.glob('*.sql'))
    if not arquivos:
        raise FileNotFoundError(f'Nenhuma migração encontrada em {pasta}')
    aplicadas = []
    with conexao.transaction():
        conexao.execute(
            'CREATE TABLE IF NOT EXISTS schema_migracoes ('
            'nome TEXT PRIMARY KEY, aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now())'
        )
        ja = {linha[0] for linha in conexao.execute('SELECT nome FROM schema_migracoes')}
        for arquivo in arquivos:
            if arquivo.name in ja:
                continue
            conexao.execute(arquivo.read_text(encoding='utf-8'))
            conexao.execute('INSERT INTO schema_migracoes (nome) VALUES (%s)', (arquivo.name,))
            aplicadas.append(arquivo.name)
    return aplicadas
