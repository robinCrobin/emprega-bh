# EmpregaBH | Parte de Sthel Felipe Torres

Entrega inicial de infraestrutura de desenvolvimento, ambiente local,
coordenacao de testes e documentacao. Data de preparacao: 18/11/2026.
Entrega do grupo: 06/12/2026.

## O que este pacote entrega

- A01: estrutura de projeto, convencoes Git, template de PR e workflow de CI.
- A02: Compose com PostgreSQL, FastAPI e base React; variaveis documentadas;
  dependencias Python com hashes, npm lock e imagens Docker por digest.
- A18: orientacoes para consolidar os testes de cada frente.
- A19: estrategia e matriz de integracao e ponta a ponta.
- A20: smoke de infraestrutura e medidor de latencia HTTP; roteiro de verificacao
  de instalacao limpa, responsividade e tempo visual de consulta.
- A21: instrucoes, responsabilidades e roteiro inicial de demonstracao.

Este pacote nao contem a coleta CKAN, esquema das tabelas de negocio, endpoints
de ocupacoes, modelo de previsao ou tela de consulta do sistema. Essas entregas
pertencem aos demais integrantes. A API possui somente /healthz e /readyz.
A tela React apenas confirma que a base de desenvolvimento esta disponivel.
Nao ha historico, previsao, MAE/RMSE ou teste funcional aprovado ficticiamente.

## Inicio com Docker

Requisitos: Git, Python 3 para gerar o .env e Docker com Compose v2. No Windows,
usar Docker Desktop com suporte a containers Linux. Na primeira execucao e
necessaria internet para baixar imagens e dependencias.

Na raiz do projeto:

```sh
python scripts/setup_env.py
docker compose up --build -d --wait --wait-timeout 180
python scripts/check_stack.py
```

Se o sistema usar python3 como nome do comando, substituir python por python3.
O setup gera senha local e preserva um .env existente. Nao enviar .env ao grupo
ou ao GitHub. A porta publicada do PostgreSQL e 5433; entre containers e 5432.

| Servico | Endereco local | Verificacao |
| --- | --- | --- |
| Interface inicial | http://localhost:5173 | Base React |
| API | http://localhost:8000/docs | Documentacao OpenAPI |
| API ativa | http://localhost:8000/healthz | Nao depende do banco |
| API e banco | http://localhost:8000/readyz | Executa SELECT 1; nao valida tabelas de negocio |
| PostgreSQL | 127.0.0.1:5433 | Usuario e banco empregabh; senha no .env |

O proxy /api do Vite encaminha chamadas do navegador para a API. No browser,
usar VITE_API_BASE_URL=/api e nunca o hostname Docker api. Para acesso direto a
API, atualizar API_CORS_ORIGINS e a configuracao do frontend de forma coerente.

Os containers deste pacote sao para desenvolvimento e demonstracao local.
A API roda sem reload; apos alterar backend, usar docker compose restart api.
Apos alterar frontend ou dependencias, usar docker compose up --build -d.
O volume pgdata preserva o banco ao parar e reiniciar a aplicacao.

## Variaveis de ambiente

| Variavel | Valor inicial | Uso |
| --- | --- | --- |
| POSTGRES_DB | empregabh | Nome do banco |
| POSTGRES_USER | empregabh | Usuario local |
| POSTGRES_PASSWORD | Gerada pelo setup | Senha local; nao versionar |
| DB_PORT | 5433 | Porta do banco no computador |
| API_PORT | 8000 | Porta da API no computador |
| WEB_PORT | 5173 | Porta da interface no computador |
| API_CORS_ORIGINS | localhost e 127.0.0.1 na porta 5173 | Origens de navegador permitidas |
| VITE_API_BASE_URL | /api | Endereco publico relativo; nunca colocar segredo |
| PGHOST e PGPORT | db e 5432 no Compose | Conexao da API dentro da rede Docker |
| API_PROXY_TARGET | http://api:8000 no Compose | Destino interno do proxy Vite |

Se alterar WEB_PORT, ajustar tambem as origens CORS. Para o smoke com portas
diferentes, usar --api http://127.0.0.1:N --web http://127.0.0.1:M.
Variaveis VITE_ podem aparecer no JavaScript entregue ao navegador.

## Execucao sem containers

Usar Python 3.12.14, Node 24.22.3 e PostgreSQL 17.10 com banco criado pelo grupo.
O caminho recomendado e Compose; a alternativa abaixo exige PostgreSQL ja ativo.

Linux e macOS, na raiz:

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements-dev.txt
python scripts/setup_env.py
```

Configurar .env com o usuario, banco, senha e porta do PostgreSQL existente.
Em um terminal, executar na raiz:

```sh
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Em outro terminal:

```sh
cd frontend
npm ci
npm run dev
```

No PowerShell, os caminhos equivalentes sao .venv\Scripts\python.exe e
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000.
Nao e preciso ativar o ambiente virtual. O backend le o .env da raiz, sem
sobrescrever variaveis ja definidas no processo.

## Verificacoes

Linux e macOS, na raiz:

```sh
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
```

PowerShell:

```powershell
$env:PYTHONPATH = 'backend'
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Frontend: executar npm ci e npm run build na pasta frontend.
Com os servicos ativos, executar python scripts/check_stack.py. Esse comando
valida apenas a infraestrutura, inclusive o proxy; nao valida busca ou previsao.

O workflow .github/workflows/ci.yml instala dependencias travadas, roda os testes
do backend, verifica /readyz com PostgreSQL real, compila o frontend e executa
o Compose com smoke. So havera resultado de CI depois de o pacote estar no
repositorio real e o GitHub Actions executar. Consulte docs/VALIDACAO.md para
as verificacoes realmente executadas durante a preparacao.

## Acompanhamento

- docs/CONTRIBUICAO.md: frentes, caminhos e fluxo Git.
- docs/PLANO_TESTES.md: integracao, ponta a ponta e criterios de aceite.
- docs/matriz_testes.csv: registro editavel, inicialmente Nao executado.
- docs/DEMONSTRACAO.md: sequencia de apresentacao apos integrar o sistema.
- docs/ANALISE_DOCUMENTOS.md: ajustes de criterios e decisoes a alinhar.
- docs/VALIDACAO.md: resultado da base e validacoes pendentes.
- docs/DADOS_E_INTEGRACAO.md: contrato dos CSVs, schema PostgreSQL sugerido e endpoints planejados.
- docs/Relatorio_Sthel_EmpregaBH.pdf: resumo para compartilhar.

Dados reais e modelos devem ser adicionados pelos responsaveis de cada frente,
mantendo a rastreabilidade da fonte e das versoes. Registrar resultados reais
no CSV antes de declarar a integracao concluida.

## Operacao local

```sh
docker compose ps
docker compose logs --tail=100 api
docker compose down
```

down preserva o volume. Nao remover volumes como rotina de correcao: a remocao
apaga os dados locais. Alterar a senha no .env de um banco ja inicializado nao
altera automaticamente a senha armazenada no PostgreSQL; atualizar o usuario
no banco quando necessario. Publicacao Vercel/Render/Neon e uma etapa posterior
ao funcionamento e a validacao das frentes.
