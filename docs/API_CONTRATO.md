# Contrato da API EmpregaBH (A09)

Base local: `http://localhost:8000` (documentação interativa em `/docs`). No navegador,
use o proxy do Vite: `/api/...` (o prefixo `/api` é removido pelo proxy; a API não tem prefixo).
Todas as rotas são `GET`, somente leitura, e usam apenas dados já gravados no PostgreSQL.

Identificador: `id` numérico da ocupação (campo `id`). O `codigo_cbo` também é devolvido.

Erros: `{"detail": "mensagem em português"}`. `404` ocupação inexistente; `422` parâmetro inválido;
`503` banco indisponível.

## `GET /ocupacoes?q=<texto>&limit=<n>`
`q` obrigatório (2 a 100 caracteres), ignora acento e caixa; todas as palavras devem aparecer no nome.
`limit` padrão 20, máximo 50 (configurável).
```json
{"termo": "tecnico", "total_retornado": 1,
 "resultados": [{"id": 3, "nome": "Técnico em enfermagem", "codigo_cbo": "999103"}]}
```

## `GET /ocupacoes/{id}`
```json
{"id": 3, "nome": "Técnico em enfermagem", "codigo_cbo": "999103",
 "total_trimestres": 16, "primeiro_periodo": "2021-T1", "ultimo_periodo": "2024-T4"}
```

## `GET /ocupacoes/{id}/serie`
Série cronológica (RF02), tendência (RF03) e campos de previsão (contrato para a A13).
```json
{
  "ocupacao": {"id": 1, "nome": "Analista de sistemas", "codigo_cbo": "999101"},
  "total_trimestres": 24,
  "serie": [{"periodo": "2021-T1", "ano": 2021, "trimestre": 1, "quantidade_vagas": 60}],
  "tendencia": {
    "disponivel": true, "classificacao": "crescente", "variacao_percentual": 22.4,
    "soma_recente": 300, "soma_anterior": 245,
    "periodo_recente": {"inicio": "2026-T1", "fim": "2026-T4"},
    "periodo_anterior": {"inicio": "2025-T1", "fim": "2025-T4"},
    "frase": "As vagas desta ocupação estão crescendo: foram 300 nos últimos 4 trimestres com dados, contra 245 nos 4 anteriores (+22.4%).",
    "motivo": null
  },
  "historico_suficiente": true,
  "minimo_trimestres": 8,
  "previsao": {"trimestre_alvo": "2027-T1", "quantidade_estimada": 78.5, "algoritmo": "regressao_linear"},
  "motivo_sem_previsao": null,
  "aviso": "Esta previsão é uma estimativa gerada por inteligência artificial ... não é uma recomendação profissional.",
  "informacoes_usadas": [
    {"chave": "historico", "descricao": "..."},
    {"chave": "sazonalidade", "descricao": "..."},
    {"chave": "tendencia_recente", "descricao": "..."}
  ]
}
```
Regras:
- `classificacao`: `crescente` (> +10%), `decrescente` (< −10%) ou `estável` (limites inclusos).
  Compara a soma dos últimos 4 trimestres **com dados** com a dos 4 anteriores.
- Tendência indisponível (`disponivel: false`, `motivo` preenchido, demais campos `null`) com menos de
  8 trimestres ou quando a base anterior é zero.
- Histórico insuficiente (< `minimo_trimestres`): `previsao: null`, `historico_suficiente: false`,
  `motivo_sem_previsao` preenchido e `informacoes_usadas: []`.
- Histórico suficiente mas sem linha na tabela `previsao` para o trimestre seguinte ao último com dados:
  `previsao: null` e `motivo_sem_previsao` informa que ainda não foi gerada.
- `aviso` (RF06) vem sempre. Nunca há CNPJ, identificador de vaga ou registro individual.

Infraestrutura (Sthel): `GET /healthz` (processo) e `GET /readyz` (processo + banco).
