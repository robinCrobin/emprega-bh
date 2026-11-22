"""Comandos: python -m app.banco.cli {migrar|carregar|seed}  (rodar com PYTHONPATH=backend)."""
import argparse
import sys
from pathlib import Path

import psycopg

from app.banco.carga import ErroCarga, carregar_csv
from app.banco.migracoes import aplicar_migracoes
from app.config import database_options

RAIZ = Path(__file__).resolve().parents[3]
CSV_PADRAO = RAIZ / 'data' / 'processed' / 'vagas_por_ocupacao_trimestre.csv'
CSV_SEED = RAIZ / 'database' / 'seeds' / 'vagas_exemplo_ficticio.csv'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Banco do EmpregaBH')
    sub = parser.add_subparsers(dest='comando', required=True)
    sub.add_parser('migrar', help='aplica o esquema (idempotente)')
    carregar = sub.add_parser('carregar', help='carrega o CSV agregado da Roberta (upsert)')
    carregar.add_argument('--arquivo', type=Path, default=CSV_PADRAO)
    sub.add_parser('seed', help='carrega dados FICTÍCIOS de exemplo (apenas desenvolvimento)')
    args = parser.parse_args(argv)
    try:
        with psycopg.connect(**database_options()) as conexao:
            if args.comando == 'migrar':
                aplicadas = aplicar_migracoes(conexao)
                print(f'Migrações aplicadas: {aplicadas or "nenhuma (já atualizado)"}')
            else:
                arquivo = CSV_SEED if args.comando == 'seed' else args.arquivo
                if not arquivo.exists():
                    print(f'Arquivo não encontrado: {arquivo}', file=sys.stderr)
                    return 1
                resumo = carregar_csv(conexao, arquivo)
                print(f'Carga concluída: {resumo.ocupacoes} ocupações, '
                      f'{resumo.linhas_vagas} linhas de vagas, {resumo.linhas_ignoradas} ignoradas.')
    except ErroCarga as erro:
        print(f'Arquivo inválido, nada foi gravado: {erro}', file=sys.stderr)
        return 1
    except psycopg.Error as erro:
        print(f'Erro de banco: {type(erro).__name__}. Verifique o .env e se o PostgreSQL está ativo.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
