# Dados e integração técnica — EmpregaBH

Este documento descreve a entrega da frente de dados, os formatos disponíveis
para integração e o contrato esperado de banco e API. Ele complementa o README
principal e não substitui a implementação das migrations ou dos endpoints.

## Resumo da entrega

A frente de dados disponibiliza:

- rotina reproduzível de coleta e agregação CKAN;
- dicionário consolidado com ocupações originais, nomes padronizados e CBO;
- série agregada por ocupação padronizada, CBO e trimestre;
- manifesto com origem dos recursos e rastreabilidade da coleta;
- casos pendentes vazios após a revisão humana registrada no dicionário.

O histórico processado contém 5.600 linhas, 627 códigos CBO distintos e cobre
24 trimestres de `2021-T1` a `2026-T4`. Os dados são o resultado da execução real
do CKAN em 20/11/2026 e não são valores simulados.

## Arquivos disponíveis

| Arquivo | Uso | Observação |
| --- | --- | --- |
| `dicionario_cbo_empregaBh.csv` | Fonte revisada da padronização | 1.817 ocupações com CBO validado |
| `pipeline/mapeamento_ocupacoes_cbo.csv` | Entrada técnica do ETL | Mesmo conteúdo convertido para o contrato do pipeline |
| `data/processed/vagas_por_ocupacao_trimestre.csv` | Importação para PostgreSQL ou consulta direta | Arquivo gerado localmente pelo pipeline |
| `reports/local/vagas_ckan_manifest.json` | Rastreabilidade da coleta | URLs, IDs, data e hash do bundle de fontes |
| `reports/local/ocupacoes_para_revisao.csv` | Revisões pendentes | Atualmente vazio |
| `pipeline/ckan_vagas.py` | Execução da coleta, limpeza e agregação | Não exige pandas ou pacotes externos |

Os arquivos em `data/processed/` e `reports/local/` seguem excluídos do Git pela
configuração atual, conforme [`.gitignore`](/Users/lobel/facul/emprega-bh/.gitignore).
O dicionário validado e o código do ETL são versionáveis. A carga em PostgreSQL
deve ser feita a partir de uma cópia gerada pela mesma versão do pipeline.

## Contrato do arquivo agregado

Arquivo: `data/processed/vagas_por_ocupacao_trimestre.csv`

| Coluna | Tipo esperado | Obrigatória | Regra |
| --- | --- | ---: | --- |
| `nome_padronizado` | `text` | Sim | Nome único adotado após a padronização |
| `codigo_cbo` | `text/string` | Sim | CBO com seis dígitos, inclusive possíveis zeros à esquerda |
| `status_validacao` | `text` | Sim | Neste arquivo, todas as linhas são `validado` |
| `quarter` | `text` | Sim | Formato `AAAA-TN`, com N de 1 a 4 |
| `vacancies` | `integer` | Sim | Quantidade agregada de vagas ofertadas no trimestre |

Regras importantes:

- não armazenar CNPJ ou identificador individual de vaga;
- não ordenar ou interpretar lacunas como zero vagas sem confirmar a cobertura;
- o CBO deve ser persistido como texto no banco;
- a chave técnica de uma ocupação é `codigo_cbo`;
- `nome_padronizado` é informação descritiva e não deve substituir o CBO como identidade;
- `quarter` deve seguir o formato oficial descrito acima;
- uma combinação válida deve ser única por CBO e trimestre.

## Contrato do dicionário CBO

Arquivo: `dicionario_cbo_empregaBh.csv`

| Coluna | Tipo esperado | Uso |
| --- | --- | --- |
| `nome_ocupacao_original` | `text` | Nome recebido da PBH |
| `nome_ocupacao_padronizado` | `text` | Nome adotado pelo EmpregaBH |
| `codigo_cbo` | `text` | Código CBO validado |
| `similaridade_textual_selecao_pct` | `decimal/null` | Evidência auxiliar de seleção, quando disponível |
| `criterio_selecao` | `text` | Justificativa da escolha humana |
| `status` | `text` | Nesta versão: `validado` |

O arquivo técnico usado pelo ETL possui outra estrutura explícita:

- `nome_original_referencia`;
- `nome_chave_normalizada`;
- `nome_padronizado`;
- `codigo_cbo`;
- `status_validacao`;
- `criterio_correspondencia`.

Na integração, manter o dicionário revisado como fonte de auditoria e o arquivo
teórico técnico como entrada da carga automática.

## Como gerar os dados

Na raiz do projeto:

```powershell
C:/Users/lobel/AppData/Local/Programs/Python/Python313/python.exe pipeline/ckan_vagas.py
```

Os arquivos resultantes são:

```text
data/processed/vagas_por_ocupacao_trimestre.csv
reports/local/vagas_ckan_manifest.json
reports/local/ocupacoes_para_revisao.csv
```

A rotina consulta novamente o CKAN. A execução não substitui dados do banco.
Ela cria uma nova carga candidata, que deve ser importada explicitamente para
depois de revisar o manifesto e o hash da geração.

Não versionar dados brutos locais nem usar o CSV processado como banco de
produção sem um esquema e migration definidos.

## Sugestão de schema PostgreSQL

A implementação pode seguir a estrutura abaixo. O nome exato das tabelas,
constraints e migrations continua responsabilidade da frente de banco.

```sql
CREATE TABLE ocupacoes (
    codigo_cbo TEXT PRIMARY KEY,
    nome_padronizado TEXT NOT NULL
);

CREATE TABLE historico_vagas (
    codigo_cbo TEXT NOT NULL REFERENCES ocupacoes(codigo_cbo),
    quarter TEXT NOT NULL,
    vacancies INTEGER NOT NULL CHECK (vacancies >= 0),
    PRIMARY KEY (codigo_cbo, quarter)
);

CREATE INDEX idx_historico_vagas_quarter
    ON historico_vagas (quarter);
```

Constraint adicional para `quarter`: validar o padrão `AAAA-T[1-4]` no
PostgreSQL ou na rotina de carga. Não transformá-lo em data ou mês antes de
documentar a semântica, pois a unidade temporal do projeto é trimestral.

Importação direta com `psql`:

```sql
\\copy ocupacoes (codigo_cbo, nome_padronizado)
FROM 'data/processed/vagas_por_ocupacao_trimestre.csv'
WITH (FORMAT csv, HEADER true);
```

O exemplo acima não deve ser executado diretamente porque o CSV agregado repete
nomes e CBO por trimestre. Primeiro consolidar ocupações com `SELECT DISTINCT`,
ou realizar a carga em uma tabela temporária e fazer o `INSERT` para cada tabela.
Uma carga segura pode usar `COPY` após criar uma tabela temporária com as cinco
colunas do arquivo processado.

## Contrato da API

A API atual ainda expõe somente:

- `GET /healthz` — disponibilidade do processo;
- `GET /readyz` — conexão com o PostgreSQL, sem validar tabelas de negócio;
- `/docs` — interface OpenAPI.

O README não deve declarar endpoints funcionais enquanto eles não existirem.
Após criar o banco, a integração pode começar pelos seguintes contratos,
propostos para serem implementados pela frente de backend:

```http
GET /ocupacoes?q={termo}
GET /ocupacoes/{codigo_cbo}
GET /ocupacoes/{codigo_cbo}/historico
GET /ocupacoes/{codigo_cbo}/previsao
```

Exemplo de resposta histórica:

```json
{
  "codigo_cbo": "252105",
  "nome_padronizado": "Administrador",
  "historico": [
    {"quarter": "2026-T1", "vacancies": 18},
    {"quarter": "2026-T2", "vacancies": 20}
  ],
  "previsao": null,
  "motivo_sem_previsao": "Histórico inferior ao mínimo de oito trimestres"
}
```

Contratos de implementação:

- busca por nome deve tolerar caixa e acentos;
- os resultados devem usar CBO como identificador estável;
- a API não deve coletar o CKAN nem executar treino em uma consulta;
- previsões devem ser pré-calculadas e persistidas, conforme a arquitetura;
- ocupações com menos de oito trimestres válidos devem retornar `previsao: null`
  e um motivo;
- não incluir CNPJ, IDs individuais de vaga ou dados pessoais;
- o aviso de que a previsão é uma estimativa pertence à resposta e à interface.

## Uso do CSV sem API

Para desenvolvimento isolado ou integração inicial, o banco pode consumir o CSV
diretamente. O caminho recomendado é:

1. executar o pipeline;
2. revisar o manifesto e o arquivo agregado;
3. aplicar migrations;
4. carregar ocupações distintas;
5. carregar uma linha por CBO e trimestre;
6. executar testes da carga;
7. implementar e testar os endpoints contra o banco;
8. conectar o frontend aos endpoints, não ao arquivo local.

O CSV é uma fonte de carga e não um substituto da API em produção. Em especial,
o frontend não deve depender de arquivo processado acessível no navegador.

## Evidências desta entrega

- 1.817 ocupações revisadas no dicionário CBO;
- 5.600 linhas agregadas no histórico processado;
- 627 CBO distintos;
- 24 trimestres presentes;
- 120.274 vagas somadas na agregação atual;
- 10 testes unitários da rotina de dados aprovados;
- 0 ocupações pendentes no relatório de revisão.

A implementação da frente seguinte deve registrar uma nova versão e um novo
manifesto em cada atualização dos dados ou do modelo.
