# Frente PostgreSQL

Nicolas cria as migrations, tabelas e carga dos dados. A configuracao deste
pacote inicia um PostgreSQL vazio e permite verificar a conexao com SELECT 1.
O healthcheck nao comprova a existencia das tabelas do sistema.

Versionar scripts de esquema nesta pasta e documentar comandos de aplicacao.
Scripts em /docker-entrypoint-initdb.d so executam na criacao inicial do volume;
ao usar esse comportamento como substituto para migrations incrementais.

## Dados disponíveis para carga

A frente de dados disponibiliza
`data/processed/vagas_por_ocupacao_trimestre.csv` com estas colunas:

- `nome_padronizado`: text, nome descritivo da ocupação;
- `codigo_cbo`: text, identificador estável de seis dígitos;
- `status_validacao`: text, nesta entrega todas as linhas são `validado`;
- `quarter`: text, formato `AAAA-TN`;
- `vacancies`: integer, quantidade agregada do trimestre.

A chave lógica recomendada é `codigo_cbo + quarter`. Usar `codigo_cbo` como
texto preserva eventuais zeros à esquerda. Não considerar lacunas do arquivo
como zero vagas sem uma regra explícita de cobertura da fonte.

Consultar `docs/DADOS_E_INTEGRACAO.md` para o contrato completo, o schema
sugerido, a carga incremental e os contratos planejados da API.

---

# Esquema, carga e consulta (A07 e A08, Nicolas)

## Tabelas (`database/migrations/001_esquema_inicial.sql`)

| Tabela | Conteúdo |
| --- | --- |
| `ocupacao` | `id` (PK), `codigo_cbo` (texto, único), `nome`, `nome_normalizado` (busca; índice GIN `pg_trgm`) |
| `vagas_trimestre` | PK `(ocupacao_id, ano, trimestre)`, `quantidade_vagas >= 0`, `trimestre` de 1 a 4 |
| `previsao` | PK `(ocupacao_id, ano_alvo, trimestre_alvo)`, `quantidade_prevista`, `algoritmo`, `gerado_em` (Davi/A13 grava; a API só lê) |
| `metrica_modelo` | `algoritmo`, `mae`, `rmse`, `data_execucao`, `observacoes` (Davi grava) |

Só há dados agregados: nenhuma coluna de CNPJ, identificador de vaga ou registro individual.
O script é idempotente e é aplicado em ordem por `python -m app.banco.cli migrar`
(controle na tabela `schema_migracoes`). Novas alterações devem ser novos arquivos `002_*.sql`.

Mapeamento do CSV da Roberta: `nome_padronizado`→`ocupacao.nome`, `codigo_cbo`→`ocupacao.codigo_cbo`,
`quarter` (`AAAA-TN`)→`ano`+`trimestre`, `vacancies`→`quantidade_vagas`. Linhas com
`status_validacao` diferente de `validado` são ignoradas. Lacunas não viram zero.

## Comandos (na raiz, com o PostgreSQL ativo e o `.env` criado)

```powershell
python scripts/setup_env.py
docker compose up -d db --wait
$env:PYTHONPATH = "backend"
.venv\Scripts\python.exe -m app.banco.cli migrar      # cria/atualiza o esquema
.venv\Scripts\python.exe -m app.banco.cli carregar    # carrega data/processed/vagas_por_ocupacao_trimestre.csv
.venv\Scripts\python.exe -m app.banco.cli seed        # SÓ DESENVOLVIMENTO: dados FICTÍCIOS (CBO 9991xx)
```

No Linux/macOS use `.venv/bin/python` e `PYTHONPATH=backend`. A carga é um upsert em transação
única: reexecutar não duplica e um arquivo inválido não grava nada. A conexão vem de
`PGHOST`/`PGPORT`/`POSTGRES_*` (padrão: PostgreSQL local na porta 5433). Não misture o seed fictício com
dados reais em um banco de demonstração.