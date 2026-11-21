# Frente de dados e modelo

## Coleta, limpeza e agregacao CKAN

A rotina em `ckan_vagas.py` consulta o catalogo CKAN da PBH, identifica os CSVs
da chave `vagas-ofertadas-pbh`, remove campos pessoais da saida processada e
agrega os registros por ocupacao normalizada e trimestre.

Executar na raiz:

```powershell
C:/Users/lobel/AppData/Local/Programs/Python/Python313/python.exe pipeline/ckan_vagas.py
```

Para desenvolvimento com `.venv`, o comando equivalente pode usar
`.venv\Scripts\python.exe pipeline/ckan_vagas.py`. A rotina utiliza somente a
biblioteca padrao do Python. Ela gera:

- `data/processed/vagas_por_ocupacao_trimestre.csv`: ocupacao padronizada, CBO, status, trimestre e vagas;
- `reports/local/vagas_ckan_manifest.json`: origem, recursos e data da coleta.

Nao processar nem versionar CNPJ ou identificador individual de vaga. Dados brutos
e modelos continuarao fora do Git conforme `.gitignore`. Cada execucao deve
registrar as versoes dos recursos acessados no manifesto antes da carga no banco.

## Padronizacao de ocupacoes

A rotina remove acentos, caixa, pontuacao e asteriscos para formar uma chave
de consulta separada do nome original da PBH. O mapeamento versionado fica em
`pipeline/mapeamento_ocupacoes_cbo.csv` e segue a especificacao de padronizacao.
A entrega atual contém 1.817 ocupações validadas no dicionário revisado.
Novos CBOs não devem ser inferidos automaticamente.

Somente entradas `validado` recebem nome padronizado e CBO. Entradas `pendente`
e ocupacoes sem correspondencia sao preservadas e registradas em
`reports/local/ocupacoes_para_revisao.csv`. O CSV processado usa CBO como
identificador quando disponivel e uma chave interna pela ocupacao normalizada
nos demais casos.

## Testes

```powershell
$env:PYTHONPATH = 'backend'
.venv\Scripts\python.exe -m unittest backend/tests/test_data_pipeline.py -v
```

Os testes cobrem normalizacao, deduplicacao, agregacao trimestral e exclusao dos
campos pessoais no formato processado.

Davi implementara treino, avaliacao e previsao em `models/`. Roberta e Davi devem
usar a serie processada sem preencher trimestres ausentes automaticamente: lacuna
de cobertura nao equivale a zero vagas.
