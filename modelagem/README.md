# Modelagem de IA (A10, A11, A12) — Davi José Ferreira

Previsao de vagas do proximo trimestre por ocupacao (CBO), a partir da serie
agregada gerada pelo pipeline (`data/processed/vagas_por_ocupacao_trimestre.csv`).
Codigo versionado aqui; artefatos binarios ficam em `models/` (fora do Git).

## Como executar

Python 3.12, na raiz do projeto. As dependencias ficam separadas das do backend,
para manter scikit-learn e pandas fora da imagem da API.

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r modelagem/requirements.txt
.venv/bin/python pipeline/ckan_vagas.py          # gera o CSV e o manifesto de coleta
.venv/bin/python -m modelagem.treinar            # treina, compara, avalia e preve
.venv/bin/python -m unittest discover -s modelagem/tests -t . -v
```

No PowerShell, usar `.venv\Scripts\python.exe`. Opcoes do treino:
`--data-referencia AAAA-MM-DD`, `--minimo-trimestres N` (padrao: variavel
`MIN_TRIMESTRES_PREVISAO` ou 8), `--trimestres-teste 4`, `--dobras-validacao 4`.

Saidas (todas ignoradas pelo Git):

| Arquivo | Conteudo |
| --- | --- |
| `models/modelo_vagas.joblib` | Modelo final e lista de variaveis |
| `models/manifesto_modelo.json` | Hash dos dados, semente, divisao, parametros, MAE/RMSE, versoes |
| `reports/local/avaliacao_modelo.md` | Relatorio legivel da avaliacao (evidencia do CT-ML-01) |
| `data/processed/previsoes_proximo_trimestre.csv` | Uma previsao por CBO elegivel |
| `reports/local/ocupacoes_sem_previsao.csv` | CBOs sem previsao e o motivo |

Para gravar no PostgreSQL (apos `python -m app.banco.cli migrar` e a carga do
historico): `python -m modelagem.banco`. Insere MAE/RMSE em `metrica_modelo` e
faz upsert em `previsao` pelo `codigo_cbo`, com `algoritmo` no formato de
identificador do contrato da API (`random_forest`, `regressao_linear`,
`media_4_trimestres`); previsoes antigas do mesmo trimestre
alvo para ocupacoes que deixaram de ser elegiveis sao removidas. A API so le
essas tabelas; a integracao com a API e a A13.

## A10 — Variaveis e divisao temporal

- Exemplo = (ocupacao, trimestre alvo). Variaveis: `defasagem_1..4` (vagas nos
  4 trimestres imediatamente anteriores) e `trimestre_2..4` (trimestre do ano em
  one-hot; T1 e a referencia). Alvo: vagas no trimestre.
- Lacunas nao viram zero: se faltar qualquer um dos 4 trimestres anteriores, o
  exemplo nao e criado (a base so tem linhas onde houve vagas e nao distingue
  falta de oferta de falta de cobertura).
- Trimestres ainda em andamento na data da coleta (`collected_at` do manifesto
  do pipeline) sao descartados. Na coleta de 27/11/2026, 2026-T4 tinha so 2 vagas.
- Divisao cronologica pelo trimestre alvo: os ultimos 4 trimestres sao teste e
  todo exemplo de treino e anterior a todo exemplo de teste. Sem embaralhamento.
- Linhas sem CBO valido de 6 digitos sao descartadas. Linhas repetidas do mesmo
  CBO no mesmo trimestre (nomes padronizados diferentes) tem as vagas somadas,
  pois o CBO e a identidade da ocupacao no contrato de dados.

## A11 — Comparacao de modelos

- Candidatos: `LinearRegression` e `RandomForestRegressor` (300 arvores,
  `random_state=42`, grade `max_depth` em {None, 8} x `min_samples_leaf` em {1, 5}).
- Um unico modelo para todas as ocupacoes (8 trimestres por ocupacao sao poucos
  para um modelo por serie).
- Escolha por validacao expansiva DENTRO do treino: para cada um dos ultimos 4
  trimestres do treino, ajusta com o passado e valida naquele trimestre. Menor
  MAE vence; RMSE desempata. O teste so e usado depois da escolha.
- Referencia ingenua: media dos 4 trimestres anteriores, nos mesmos exemplos.
- O modelo final reaproveita a configuracao escolhida, reajustada com treino e
  teste, e preve o trimestre seguinte ao ultimo trimestre fechado.

## A12 — Avaliacao e regra minima

- Metricas: MAE e RMSE (scikit-learn), em vagas. Previsoes limitadas a >= 0.
- Regra minima: so ha previsao com pelo menos 8 trimestres com dados ANTES do
  alvo e com os 4 trimestres imediatamente anteriores presentes. A regra vale
  tanto para criar exemplos de treino quanto para gerar previsoes.
- Consequencia: so recebem previsao ocupacoes com dado no ultimo trimestre
  fechado, que e exatamente o trimestre que a API consulta
  (`proximo_trimestre` do ultimo periodo da ocupacao).

## Resultado da execucao de 27/11/2026 (dados reais do CKAN)

Coleta de 27/11/2026, 23 recursos; 2021-T1 a 2026-T3; 626 CBOs.

| Conjunto | Periodo | Exemplos | Ocupacoes |
| --- | --- | ---: | ---: |
| Treino | 2023-T1 a 2025-T3 | 726 | 106 |
| Teste | 2025-T4 a 2026-T3 | 296 | 90 |

Validacao dentro do treino (MAE / RMSE): regressao linear 85,67 / 210,16;
melhor Random Forest (`max_depth=8, min_samples_leaf=5`) 72,80 / 187,84;
referencia 52,57 / 157,70. Escolhido: Random Forest.

| Teste reservado | MAE | RMSE |
| --- | ---: | ---: |
| Regressao Linear | 65,08 | 150,99 |
| Random Forest Regressor (escolhido) | 59,93 | 146,23 |
| Media dos 4 trimestres anteriores | 61,44 | 172,46 |

Previsoes para 2026-T4: 80 ocupacoes; 546 sem previsao (462 por menos de 8
trimestres, 84 por falta de dados em algum dos 4 trimestres anteriores).

Leitura honesta: no teste o Random Forest ficou abaixo da referencia em MAE e
RMSE, mas na validacao a referencia foi melhor que os dois modelos. Com uma
unica avaliacao nao ha evidencia de ganho estavel; recomenda-se reavaliar a
cada nova coleta e manter a referencia no relatorio.

## Limitacoes

- A previsao e estimativa, nao garantia de vaga nem recomendacao profissional.
- A base muda bastante de volume a partir de 2024; o modelo assume continuidade.
- RMSE alto indica erros grandes concentrados em ocupacoes de muito volume.
- O artefato `.joblib` depende da mesma versao de scikit-learn para ser lido.
