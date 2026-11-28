"""Treino, comparacao e avaliacao do modelo de previsao de vagas (A10-A12).

Uso (na raiz, com o ambiente de modelagem/requirements.txt):
    python -m modelagem.treinar

Etapas:
1. le data/processed/vagas_por_ocupacao_trimestre.csv e descarta trimestres
   ainda nao encerrados na data da coleta (manifesto do pipeline);
2. monta exemplos (4 defasagens + trimestre do ano) so onde a regra minima vale;
3. reserva os ultimos trimestres alvo para teste (divisao cronologica);
4. escolhe algoritmo/parametros por validacao expansiva DENTRO do treino;
5. avalia no teste uma unica vez: regressao linear, Random Forest e referencia;
6. reajusta o escolhido com todos os exemplos e preve o proximo trimestre.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from modelagem.avaliacao import ajustar, melhor, metricas, prever, validacao_expansiva
from modelagem.dados import (CSV_PADRAO, MANIFESTO_COLETA_PADRAO, RAIZ, ErroDados, carregar_vagas,
                             data_referencia_da_coleta, remover_trimestres_abertos, rotulo,
                             sha256_arquivo, trimestre_de_indice, ultimo_trimestre_fechado)
from modelagem.modelos import SEMENTE, candidatos, referencia
from modelagem.variaveis import (ALVO, JANELA, VARIAVEIS, divisao_temporal, minimo_trimestres,
                                 montar_entrada_previsao, montar_exemplos)

VERSAO_FORMATO = 1


@dataclass
class Configuracao:
    dados: Path = CSV_PADRAO
    manifesto_coleta: Path = MANIFESTO_COLETA_PADRAO
    data_referencia: date | None = None
    minimo_trimestres: int = field(default_factory=minimo_trimestres)
    trimestres_teste: int = 4
    dobras_validacao: int = 4
    pasta_modelos: Path = RAIZ / 'models'
    pasta_relatorios: Path = RAIZ / 'reports' / 'local'
    arquivo_previsoes: Path = RAIZ / 'data' / 'processed' / 'previsoes_proximo_trimestre.csv'


def _relativo(caminho: Path) -> str:
    try:
        return caminho.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return str(caminho)


def _arredondar(resultado: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in resultado.items()}


def _resolver_referencia(config: Configuracao) -> tuple[date, str]:
    if config.data_referencia:
        return config.data_referencia, 'parametro --data-referencia'
    coleta = data_referencia_da_coleta(config.manifesto_coleta)
    if coleta:
        return coleta, f'collected_at de {_relativo(config.manifesto_coleta)}'
    return date.today(), 'data atual (manifesto de coleta ausente)'


def executar(config: Configuracao) -> dict:
    referencia_data, origem_referencia = _resolver_referencia(config)
    dados, leitura = carregar_vagas(config.dados)
    ultimo_fechado = ultimo_trimestre_fechado(referencia_data)
    dados = remover_trimestres_abertos(dados, ultimo_fechado, leitura)
    if dados.empty:
        raise ErroDados('Nenhum trimestre fechado na base.')
    minimo = config.minimo_trimestres

    # A10: exemplos e divisao cronologica
    exemplos = montar_exemplos(dados, minimo)
    if exemplos.empty:
        raise ErroDados(f'Nenhuma ocupacao atende a regra de {minimo} trimestres com 4 anteriores consecutivos.')
    divisao = divisao_temporal(exemplos, config.trimestres_teste)
    treino, teste = divisao.treino, divisao.teste
    assert treino['alvo_indice'].max() < teste['alvo_indice'].min(), 'vazamento temporal na divisao'

    # A11/A12: selecao por validacao dentro do treino (teste intocado)
    lista = candidatos()
    validacao = [validacao_expansiva(c, treino, config.dobras_validacao) for c in lista]
    validacao_referencia = validacao_expansiva(referencia(), treino, config.dobras_validacao)
    escolhido_resultado = melhor(validacao)
    escolhido = next(c for c in lista if c.chave == escolhido_resultado['candidato'])
    melhores_por_familia: dict[str, tuple] = {}
    for c, r in zip(lista, validacao):
        atual = melhores_por_familia.get(c.familia)
        if atual is None or melhor([atual[1], r]) is r:
            melhores_por_familia[c.familia] = (c, r)

    # Avaliacao final no teste reservado (uma vez, configuracoes ja fixadas)
    resultado_teste = {}
    for familia, (candidato, _) in melhores_por_familia.items():
        resultado_teste[familia] = {'candidato': candidato.chave, 'algoritmo': candidato.nome_exibicao,
                                    **metricas(teste[ALVO], prever(ajustar(candidato, treino), teste))}
    base = referencia()
    resultado_teste[base.familia] = {'candidato': base.chave, 'algoritmo': base.nome_exibicao,
                                     **metricas(teste[ALVO], prever(ajustar(base, treino), teste))}
    teste_escolhido = resultado_teste[escolhido.familia]
    teste_base = resultado_teste[base.familia]

    # Modelo final: mesma configuracao, reajustada com treino + teste
    modelo_final = ajustar(escolhido, exemplos)
    alvo_previsao = int(dados['indice'].max()) + 1
    entrada, sem_previsao = montar_entrada_previsao(dados, alvo_previsao, minimo)
    ano_alvo, trimestre_alvo = trimestre_de_indice(alvo_previsao)
    previsoes = entrada[['codigo_cbo', 'nome_padronizado', 'trimestres_historico']].copy()
    previsoes['ano_alvo'], previsoes['trimestre_alvo'] = ano_alvo, trimestre_alvo
    previsoes['periodo_alvo'] = rotulo(alvo_previsao)
    previsoes['quantidade_prevista'] = np.round(prever(modelo_final, entrada), 2) if len(entrada) else []
    previsoes['algoritmo'] = escolhido.familia  # identificador do contrato da API
    previsoes = previsoes[['codigo_cbo', 'nome_padronizado', 'ano_alvo', 'trimestre_alvo', 'periodo_alvo',
                           'quantidade_prevista', 'algoritmo', 'trimestres_historico']]

    # Artefatos
    config.pasta_modelos.mkdir(parents=True, exist_ok=True)
    config.pasta_relatorios.mkdir(parents=True, exist_ok=True)
    config.arquivo_previsoes.parent.mkdir(parents=True, exist_ok=True)
    arquivo_modelo = config.pasta_modelos / 'modelo_vagas.joblib'
    joblib.dump({'modelo': modelo_final, 'variaveis': VARIAVEIS, 'algoritmo': escolhido.nome_exibicao,
                 'candidato': escolhido.chave, 'minimo_trimestres': minimo, 'janela': JANELA,
                 'versao_formato': VERSAO_FORMATO}, arquivo_modelo)
    previsoes.to_csv(config.arquivo_previsoes, index=False, quoting=csv.QUOTE_MINIMAL)
    arquivo_sem_previsao = config.pasta_relatorios / 'ocupacoes_sem_previsao.csv'
    sem_previsao.to_csv(arquivo_sem_previsao, index=False)

    manifesto = {
        'versao_formato': VERSAO_FORMATO,
        'gerado_em': datetime.now().astimezone().isoformat(timespec='seconds'),
        'dados': {
            'arquivo': _relativo(config.dados), 'sha256': sha256_arquivo(config.dados),
            'data_referencia': referencia_data.isoformat(), 'origem_data_referencia': origem_referencia,
            'ultimo_trimestre_fechado': rotulo(ultimo_fechado),
            'linhas_lidas': leitura.linhas_lidas, 'linhas_sem_cbo': leitura.linhas_sem_cbo,
            'linhas_nao_validadas': leitura.linhas_nao_validadas,
            'linhas_cbo_invalido': leitura.linhas_cbo_invalido,
            'exemplos_cbo_invalido': leitura.exemplos_cbo_invalido,
            'linhas_somadas_por_cbo_trimestre': leitura.linhas_consolidadas,
            'cbos_com_varios_nomes': leitura.cbos_com_varios_nomes,
            'linhas_trimestre_aberto_descartadas': leitura.linhas_trimestre_aberto,
            'trimestres_abertos_descartados': leitura.trimestres_abertos,
            'ocupacoes': int(dados['codigo_cbo'].nunique()),
            'periodo': [rotulo(int(dados['indice'].min())), rotulo(int(dados['indice'].max()))],
        },
        'regra_historico_minimo': {
            'minimo_trimestres': minimo, 'defasagens_consecutivas': JANELA,
            'lacunas': 'trimestres sem registro nao sao preenchidos com zero',
            'avaliada_em': 'dados anteriores ao trimestre alvo de cada exemplo',
        },
        'variaveis': VARIAVEIS, 'alvo': ALVO, 'semente': SEMENTE,
        'divisao_temporal': {
            'criterio': f'ultimos {config.trimestres_teste} trimestres alvo reservados para teste',
            'treino': {'periodo': list(divisao.periodos_treino), 'exemplos': len(treino),
                       'ocupacoes': int(treino['codigo_cbo'].nunique())},
            'teste': {'periodo': list(divisao.periodos_teste), 'exemplos': len(teste),
                      'ocupacoes': int(teste['codigo_cbo'].nunique())},
            'dobras_validacao': config.dobras_validacao,
        },
        'validacao': [{**_arredondar({k: v for k, v in r.items() if k != 'dobras'}),
                       'dobras': [_arredondar(d) for d in r['dobras']]}
                      for r in [*validacao, validacao_referencia]],
        'selecao': {
            'criterio': 'menor MAE na validacao expansiva dentro do treino; RMSE desempata',
            'candidato': escolhido.chave, 'familia': escolhido.familia,
            'algoritmo': escolhido.nome_exibicao, 'parametros': escolhido.parametros,
        },
        'teste': {familia: _arredondar(r) for familia, r in resultado_teste.items()},
        'escolhido_supera_referencia_na_validacao': {
            'mae': escolhido_resultado['mae'] < validacao_referencia['mae'],
            'rmse': escolhido_resultado['rmse'] < validacao_referencia['rmse'],
        },
        'escolhido_supera_referencia_no_teste': {
            'mae': teste_escolhido['mae'] < teste_base['mae'],
            'rmse': teste_escolhido['rmse'] < teste_base['rmse'],
        },
        'modelo_final': {
            'ajustado_com': 'todos os exemplos (treino + teste) apos a avaliacao',
            'exemplos': len(exemplos), 'periodo': [rotulo(int(exemplos['alvo_indice'].min())),
                                                   rotulo(int(exemplos['alvo_indice'].max()))],
            'arquivo': _relativo(arquivo_modelo), 'sha256': sha256_arquivo(arquivo_modelo),
        },
        'previsoes': {
            'trimestre_alvo': rotulo(alvo_previsao), 'arquivo': _relativo(config.arquivo_previsoes),
            'ocupacoes_com_previsao': len(previsoes), 'ocupacoes_sem_previsao': len(sem_previsao),
            'arquivo_sem_previsao': _relativo(arquivo_sem_previsao),
        },
        'ambiente': {'python': platform.python_version(), 'scikit-learn': sklearn.__version__,
                     'pandas': pd.__version__, 'numpy': np.__version__, 'joblib': joblib.__version__},
    }
    arquivo_manifesto = config.pasta_modelos / 'manifesto_modelo.json'
    arquivo_manifesto.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding='utf-8')
    arquivo_relatorio = config.pasta_relatorios / 'avaliacao_modelo.md'
    arquivo_relatorio.write_text(relatorio_markdown(manifesto), encoding='utf-8')
    manifesto['arquivos'] = {'manifesto': arquivo_manifesto, 'relatorio': arquivo_relatorio}
    return manifesto


def _fmt(valor: float) -> str:
    return f'{valor:.2f}'.replace('.', ',')


def _sim(valor: bool) -> str:
    return 'sim' if valor else 'nao'


def relatorio_markdown(m: dict) -> str:
    d, div, sel = m['dados'], m['divisao_temporal'], m['selecao']
    linhas = [
        '# Avaliacao do modelo de previsao de vagas (A10-A12)', '',
        f'Gerado em {m["gerado_em"]}. Semente: {m["semente"]}.', '',
        '## Dados', '',
        f'- Arquivo: `{d["arquivo"]}` (sha256 `{d["sha256"][:16]}...`)',
        f'- Referencia: {d["data_referencia"]} ({d["origem_data_referencia"]}); '
        f'ultimo trimestre fechado: {d["ultimo_trimestre_fechado"]}',
        f'- Periodo usado: {d["periodo"][0]} a {d["periodo"][1]}; {d["ocupacoes"]} ocupacoes com CBO',
        f'- Descartados por trimestre em andamento: {d["linhas_trimestre_aberto_descartadas"]} linha(s) '
        f'{d["trimestres_abertos_descartados"] or ""}',
        f'- Descartadas sem CBO valido de 6 digitos: {d["linhas_sem_cbo"] + d["linhas_cbo_invalido"]} linha(s) '
        f'{d["exemplos_cbo_invalido"] or ""}',
        f'- Linhas repetidas por (CBO, trimestre) somadas: {d["linhas_somadas_por_cbo_trimestre"]} '
        f'({d["cbos_com_varios_nomes"]} CBOs com mais de um nome padronizado)',
        '', '## Variaveis e regra minima', '',
        f'- Variaveis: {", ".join(m["variaveis"])}; alvo: `{m["alvo"]}`',
        f'- Exemplo so existe com >= {m["regra_historico_minimo"]["minimo_trimestres"]} trimestres com dados '
        'antes do alvo e com os 4 trimestres anteriores presentes; lacunas nao viram zero.',
        '', '## Divisao temporal', '',
        f'- Treino: {div["treino"]["periodo"][0]} a {div["treino"]["periodo"][1]} — '
        f'{div["treino"]["exemplos"]} exemplos, {div["treino"]["ocupacoes"]} ocupacoes',
        f'- Teste: {div["teste"]["periodo"][0]} a {div["teste"]["periodo"][1]} — '
        f'{div["teste"]["exemplos"]} exemplos, {div["teste"]["ocupacoes"]} ocupacoes',
        f'- Selecao por validacao expansiva nos ultimos {div["dobras_validacao"]} trimestres do treino.',
        '', '## Validacao dentro do treino', '',
        '| Candidato | MAE | RMSE | Exemplos |', '| --- | ---: | ---: | ---: |',
        *(f'| {r["candidato"]} | {_fmt(r["mae"])} | {_fmt(r["rmse"])} | {r["exemplos"]} |'
          for r in m['validacao']),
        '', f'Escolhido: **{sel["candidato"]}** ({sel["criterio"]}). '
        f'Supera a referencia na validacao: MAE {_sim(m["escolhido_supera_referencia_na_validacao"]["mae"])}, '
        f'RMSE {_sim(m["escolhido_supera_referencia_na_validacao"]["rmse"])}.',
        '', '## Teste reservado', '',
        '| Algoritmo | Configuracao | MAE | RMSE | Exemplos |', '| --- | --- | ---: | ---: | ---: |',
        *(f'| {r["algoritmo"]} | {r["candidato"]} | {_fmt(r["mae"])} | {_fmt(r["rmse"])} | {r["exemplos"]} |'
          for r in m['teste'].values()),
        '',
        f'Escolhido supera a referencia no teste: MAE {_sim(m["escolhido_supera_referencia_no_teste"]["mae"])}, '
        f'RMSE {_sim(m["escolhido_supera_referencia_no_teste"]["rmse"])}. '
        'Uma unica avaliacao nao comprova ganho ou estabilidade estatistica.',
        '', '## Previsoes', '',
        f'- Trimestre alvo: {m["previsoes"]["trimestre_alvo"]}',
        f'- Com previsao: {m["previsoes"]["ocupacoes_com_previsao"]} ocupacoes; '
        f'sem previsao: {m["previsoes"]["ocupacoes_sem_previsao"]} (motivos em `{m["previsoes"]["arquivo_sem_previsao"]}`)',
        f'- Modelo final ajustado com {m["modelo_final"]["exemplos"]} exemplos '
        f'({m["modelo_final"]["periodo"][0]} a {m["modelo_final"]["periodo"][1]})',
        '', '## Limitacoes', '',
        '- A previsao e uma estimativa, nao garantia de vaga nem recomendacao profissional.',
        '- A base so registra trimestres com vagas ofertadas; nao e possivel distinguir '
        'ausencia de oferta de ausencia de cobertura, por isso lacunas excluem exemplos.',
        '- O volume total da base muda bastante a partir de 2024; o modelo assume que o '
        'padrao recente continua.',
        '- Um modelo unico e ajustado para todas as ocupacoes; ocupacoes de volume muito '
        'diferente da maioria tendem a ter erro maior.',
        '',
    ]
    return '\n'.join(linhas)


def _data(valor: str) -> date:
    return date.fromisoformat(valor)


def main(argv: list[str] | None = None) -> int:
    padrao = Configuracao()
    parser = argparse.ArgumentParser(description='Treina e avalia o modelo de previsao de vagas (A10-A12).')
    parser.add_argument('--dados', type=Path, default=padrao.dados)
    parser.add_argument('--manifesto-coleta', type=Path, default=padrao.manifesto_coleta)
    parser.add_argument('--data-referencia', type=_data, default=None,
                        help='AAAA-MM-DD; trimestres nao encerrados nessa data sao descartados')
    parser.add_argument('--minimo-trimestres', type=int, default=padrao.minimo_trimestres)
    parser.add_argument('--trimestres-teste', type=int, default=padrao.trimestres_teste)
    parser.add_argument('--dobras-validacao', type=int, default=padrao.dobras_validacao)
    parser.add_argument('--pasta-modelos', type=Path, default=padrao.pasta_modelos)
    parser.add_argument('--pasta-relatorios', type=Path, default=padrao.pasta_relatorios)
    parser.add_argument('--arquivo-previsoes', type=Path, default=padrao.arquivo_previsoes)
    args = parser.parse_args(argv)
    config = Configuracao(
        dados=args.dados, manifesto_coleta=args.manifesto_coleta, data_referencia=args.data_referencia,
        minimo_trimestres=minimo_trimestres(args.minimo_trimestres), trimestres_teste=args.trimestres_teste,
        dobras_validacao=args.dobras_validacao, pasta_modelos=args.pasta_modelos,
        pasta_relatorios=args.pasta_relatorios, arquivo_previsoes=args.arquivo_previsoes,
    )
    try:
        m = executar(config)
    except (ErroDados, ValueError) as erro:
        print(f'Erro: {erro}', file=sys.stderr)
        return 1
    print(f'Escolhido: {m["selecao"]["candidato"]}')
    for r in m['teste'].values():
        print(f'  teste {r["algoritmo"]:<36} MAE {r["mae"]:.2f}  RMSE {r["rmse"]:.2f}  (n={r["exemplos"]})')
    print(f'Previsoes {m["previsoes"]["trimestre_alvo"]}: {m["previsoes"]["ocupacoes_com_previsao"]} ocupacoes '
          f'-> {m["previsoes"]["arquivo"]}')
    print(f'Manifesto: {_relativo(m["arquivos"]["manifesto"])}; relatorio: {_relativo(m["arquivos"]["relatorio"])}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
