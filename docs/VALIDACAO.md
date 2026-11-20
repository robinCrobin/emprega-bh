# Verificações da entrega inicial

Data: 18/11/2026. Escopo: base de infraestrutura preparada por Sthel Felipe Torres.

| Verificação | Resultado e limite |
| --- | --- |
| Instalação Python em ambiente virtual novo | Aprovada com requirements-dev.txt e hashes |
| Testes automatizados do backend | 6 testes aprovados; conexões simuladas; não comprovam PostgreSQL real |
| npm ci e npm run build | Aprovados; compilação da tela inicial React |
| HTTP nativo da API e frontend | /healthz, página inicial e proxy /api/healthz responderam corretamente |
| Banco indisponível | /readyz retornou 503 e resposta sem detalhes da conexão, conforme esperado |
| Geração de configuração | .env criado com senha aleatória; segunda execução preservou o arquivo |
| Configuração YAML | Compose e workflow passaram por leitura sintática YAML |
| Git local | Repositório inicializado em main; .env, .venv, node_modules e dist ignorados |
| Imagens Docker | Tags e digests consultados no registro oficial; imagens não foram executadas |

Comando de teste executado na raiz:

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
```

Casos aprovados: liveness independente de banco; prontidão consulta banco;
erro de banco retorna 503 sem detalhes; origem local aceita por CORS; origem
externa sem permissão CORS; porta interna do banco prevalece sobre a porta do host.

O cliente de testes emitiu aviso de depreciação de httpx na versão instalada
do Starlette. Os seis casos passaram. Revisar a migração do cliente de testes
ao atualizar as dependências.

## Verificações pendentes

- Docker/Compose e conexão real com PostgreSQL: Docker não está disponível no
  ambiente de preparação. A leitura YAML não substitui docker compose config
  nem a execução. O workflow contém essa validação para o repositório do grupo.
- CI no GitHub, proteção de branch e remoto: precisam ser configurados e
  executados no repositório real. Não houve push ou publicação.
- Validação visual no navegador: não executada neste ambiente. O build passou,
  mas isso não comprova renderização nem responsividade.
- Pipeline, dados reais, tabelas de negócio, endpoints funcionais, modelo,
  métricas MAE/RMSE, interface de consulta, integração completa, desempenho
  funcional e testes com usuários: aguardam as entregas das respectivas frentes.

A matriz funcional mantém os 20 casos como Não executado. A execução nativa de
infraestrutura não é uma aprovação do sistema completo.
