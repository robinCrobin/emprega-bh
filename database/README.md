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
