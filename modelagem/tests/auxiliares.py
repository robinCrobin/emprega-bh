"""Dados FICTICIOS para testes: nao representam a PBH."""
import csv
from pathlib import Path

CABECALHO = ['nome_padronizado', 'codigo_cbo', 'status_validacao', 'quarter', 'vacancies']


def periodo(i: int, ano_inicial: int = 2021) -> str:
    """i-esimo trimestre a partir de ano_inicial-T1."""
    return f'{ano_inicial + i // 4}-T{i % 4 + 1}'


def escrever_csv(caminho: Path, linhas: list[dict]) -> Path:
    with caminho.open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CABECALHO)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({'status_validacao': 'validado', **linha})
    return caminho


def serie(nome: str, cbo: str, vagas: list[int | None], inicio: int = 0) -> list[dict]:
    """Linhas de uma ocupacao; None representa lacuna (trimestre sem linha)."""
    return [{'nome_padronizado': nome, 'codigo_cbo': cbo, 'quarter': periodo(inicio + i), 'vacancies': v}
            for i, v in enumerate(vagas) if v is not None]
