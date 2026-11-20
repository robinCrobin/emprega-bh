# EmpregaBH

Contribuição de Sthel Felipe Torres

Infraestrutura de desenvolvimento, integração e documentação

**Preparação:** 18/11/2026 &nbsp;&nbsp; **Entrega do grupo:** 06/12/2026

Esta entrega inicial organiza o ambiente para o grupo desenvolver em paralelo e prepara a consolidação dos testes. O pacote inclui código da base, instruções, automação de verificações, uma matriz com 20 cenários e um roteiro de demonstração.

## 1 Responsabilidades e situação

| ID | Entrega de Sthel | Situação nesta etapa |
| --- | --- | --- |
| A01 | Estrutura, convenções, fluxo Git e template de PR. | Base preparada; incorporação ao GitHub do grupo pendente. |
| A02 | Compose, configuração local e dependências travadas. | Python e frontend verificados; execução Docker e banco real pendentes. |
| A18 | Consolidação dos testes de cada frente. | Orientações prontas; resultados dos colegas pendentes. |
| A19 | Integração e fluxo ponta a ponta. | Plano e matriz prontos; execução funcional depende da integração. |
| A20 | Instalação, desempenho básico e responsividade. | Scripts e critérios preparados; validação completa pendente. |
| A21 | Instruções técnicas e roteiro de demonstração. | Documentação inicial pronta; consolidar após a integração. |

**Limite da entrega:** a coleta e o tratamento de dados pertencem a Roberta; banco e API de negócio a Nicolas; modelo a Davi; interface de consulta a João Pedro. Este pacote fornece a estrutura para essas frentes e não declara o sistema completo como concluído.


---


# Organização e execução local

## 2 Base do projeto

A estrutura separa backend, frontend, pipeline, banco, dados, modelos, scripts, testes e documentação. O backend inicial expõe apenas os endpoints de infraestrutura /healthz e /readyz. A página React é uma tela inicial para desenvolvimento.

O fluxo proposto usa main como versão integrada e branches por atividade, como feat/a04-coleta-ckan e test/a19-integracao. Cada PR registra mudança, verificações e impacto na integração. A criação do remoto e a proteção de branch dependem do repositório real do grupo.

## 3 Ambiente reproduzível

O Compose prepara PostgreSQL, FastAPI e React. As dependências Python têm versões e hashes, o frontend usa package-lock.json e as imagens Docker estão fixadas por digest. O arquivo .env.example documenta a configuração sem credenciais reais.

| Configuração | Valor inicial | Finalidade |
| --- | --- | --- |
| POSTGRES_DB / USER | empregabh | Banco e usuário locais. |
| POSTGRES_PASSWORD | Gerada pelo setup | Senha local fora do Git. |
| DB_PORT | 5433 | Acesso ao PostgreSQL pelo computador. |
| API_PORT / WEB_PORT | 8000 / 5173 | Endereços locais da API e interface. |
| API_CORS_ORIGINS | localhost e 127.0.0.1:5173 | Origens permitidas no navegador. |
| VITE_API_BASE_URL | /api | Acesso do browser pelo proxy Vite. |

Com Git, Python e Docker Compose v2 instalados, executar na raiz do projeto:

```sh
python scripts/setup_env.py
docker compose up --build -d --wait --wait-timeout 180
python scripts/check_stack.py
```

Interface: http://localhost:5173. Documentação da API: http://localhost:8000/docs. A verificação /readyz executa SELECT 1 e confirma conexão; não comprova a existência das tabelas de negócio.

O README traz comandos para Windows, Linux e macOS, alternativa sem containers, ajustes de portas e operação local. O setup preserva configurações existentes. Dados, .env e modelos locais ficam fora do Git.


---


# Testes integrados

## 4 Coordenação da A18 e execução da A19

Cada responsável testa os componentes que desenvolve e entrega comandos, resultados e evidências. Sthel consolida essas informações e valida a comunicação entre as frentes. O smoke da infraestrutura é separado dos testes funcionais do sistema.

Antes de integrar, o grupo deve confirmar contratos da API, formato das séries e previsões, identificador de ocupação, versões da base e do modelo. A execução funcional usará banco de teste isolado e cargas controladas identificadas como fixtures.

| Caso ou grupo | Verificação e resultado esperado |
| --- | --- |
| CT-INT-01 | Histórico suficiente: retorno coerente do histórico e previsão numérica para o trimestre seguinte. |
| CT-INT-02 e 09 | Testar a fronteira de 7 e 8 trimestres. Abaixo de 8: previsão null e motivo; nenhum resultado fictício. |
| CT-INT-03 e 08 | Tendências crescente, estável e decrescente; limites exatos de +/-10%; base anterior zero sem divisão inválida. |
| CT-INT-04 | Busca parcial com variações de caixa e acentuação retorna as ocupações equivalentes. |
| CT-INT-05 a 07 | Carga consistente, reexecução sem duplicar contagens, API igual ao banco e consulta independente do CKAN. |
| CT-UI-01 a 04 | Gráfico, previsão, tendência, aviso e privacidade verificados na tela, DOM e respostas da API. |
| CT-E2E-01 e 02 | Validar o percurso do dado público à tela e os casos sem resultado ou sem histórico mínimo. |
| CT-ML-01 | Registrar corte temporal, amostras, algoritmo, parâmetros, MAE/RMSE e comparação com referência. |

**Registro:** docs/matriz_testes.csv contém 20 cenários com preparação, resultado esperado, apoio, estado, evidência, versão e defeito. Todos os casos funcionais começam como “Não executado”. Os detalhes e critérios estão em docs/PLANO_TESTES.md.

**Aceite:** corrigir falhas que impeçam a jornada, violem o histórico mínimo, exponham dados indevidos ou causem vazamento temporal. Casos bloqueados ou não executados não contam como aprovados.


---


# Verificações e demonstração

## 5 Verificações não funcionais da A20

| Frente | Como verificar | Evidência |
| --- | --- | --- |
| Instalação limpa | Usar nova pasta, gerar .env, instalar locks e executar os serviços. | Comandos, versões e resultado do smoke. |
| Responsividade | Validar 375, 768 e 1366 px; gráfico, aviso, foco de teclado e mensagens. | Navegador, largura e capturas do sistema integrado. |
| Usabilidade | Concluir a consulta principal em até três interações, usando unidade acordada pelo grupo. | Ações observadas e dificuldades. |
| Desempenho | Medir primeira consulta e 30 aquecidas; verificar também o tempo até o gráfico visível. | Primeira latência, média, p95, máximo e tempo visual. |
| Privacidade | Conferir interface e payloads contra os campos necessários. | Ausência de CNPJ e ID individual de vaga. |

O script measure_latency.py exige uma URL funcional real e salva as medidas HTTP. Qualquer erro ou amostra aquecida acima de 3 s reprova essa verificação. A medição HTTP não comprova o tempo de renderização do gráfico. A primeira resposta lenta de um serviço gratuito deve ser registrada separadamente.

## 6 Documentação e roteiro da A21

O README explica instalação, variáveis, comandos e operação. O roteiro final deverá apresentar objetivo e versão, busca por ocupação, histórico, tendência quando calculável, previsão com aviso, caso de histórico insuficiente e visualização em tela pequena.

Na demonstração, Davi fornece os valores reais de MAE e RMSE, os períodos de treino e teste e a referência de comparação. Sthel apresenta os registros consolidados e as limitações. A documentação final será atualizada para refletir o sistema efetivamente integrado.

**Handoff:** Roberta entrega dados e periodicidade; Nicolas entrega migrations e contratos da API; Davi entrega artefato e avaliação; João Pedro entrega a interface e comandos dos testes. Com isso, Sthel executa os cenários funcionais e fecha os registros.


---


# Ajustes para alinhar no grupo

## 7 Critérios de avaliação do modelo

**MAE e variância.** O plano compara MAE à variância natural da série. MAE é medido em vagas; variância, em vagas ao quadrado. A comparação direta precisa ser substituída por um critério coerente. A proposta é comparar MAE e RMSE com uma referência de média dos quatro trimestres anteriores, nos mesmos períodos e sem informação futura.

**Oito trimestres e quatro defasagens.** O mínimo de oito trimestres foi preservado. Porém, oito observações geram apenas quatro exemplos supervisionados completos após as quatro defasagens. Reservar o último ano inteiro para teste deixaria zero exemplos de treino nesse caso. Davi deve definir o corte após construir os exemplos e explicitar a limitação da avaliação com séries curtas.

**Escolha do algoritmo.** Para manter o teste final independente, a comparação e o ajuste de algoritmos devem usar validação temporal dentro do treino. O conjunto de teste reservado avalia a escolha final. Registrar métricas reais, sem afirmar estabilidade estatística a partir de uma amostra pequena.

## 8 Regras que precisam de confirmação

**Tendência e lacunas.** Os limites exatos de +10% e -10% são estáveis. A apresentação da tendência quando a soma anterior é zero, ou quando faltam oito períodos, precisa de regra acordada. Proposta: exibir indisponibilidade com motivo. Ausência de registro não deve virar zero vagas sem confirmar a cobertura da fonte.

**Consulta e previsão.** A arquitetura prevê resultados pré-calculados e armazenados no banco. Os testes devem refletir esse fluxo: o usuário consulta histórico e previsão persistidos, sem refazer a coleta ou o treinamento a cada requisição.

Essas observações são orientações para a integração. Os documentos originais não foram alterados e as decisões das frentes continuam com seus responsáveis.


---


# Evidências e próximos passos

## 9 Verificações realmente executadas

| Verificação | Resultado |
| --- | --- |
| Instalação Python | Ambiente virtual novo instalado com dependências travadas e hashes. |
| Testes do backend | 6 casos aprovados: liveness, prontidão, falha de conexão, CORS e porta do banco. Banco simulado. |
| Frontend | npm ci e npm run build concluídos; tela inicial compilada. |
| HTTP nativo e proxy | Página inicial, /healthz e /api/healthz responderam corretamente. |
| Banco indisponível | /readyz retornou 503 e resposta sem detalhes da conexão. |
| Configuração e Git | Setup idempotente; YAML legível; exclusões de .env e dependências confirmadas. |

**Pendente:** execução Docker/Compose e conexão real com PostgreSQL, pois Docker não está disponível no ambiente de preparação; execução do GitHub Actions no repositório real; conferência visual em navegador; todos os testes funcionais e as métricas do modelo. O build e a leitura YAML não substituem essas verificações.

O registro detalhado está em docs/VALIDACAO.md. Ele também registra o aviso de depreciação do cliente HTTP de testes, que não impediu os seis casos. Não houve push, publicação nem implantação externa.

## 10 Continuidade até a entrega

Incorporar a base ao repositório do grupo, executar o Compose em uma máquina com Docker e confirmar os contratos entre as frentes. Depois de integrar os componentes, preencher a matriz com evidências, corrigir falhas, atualizar a documentação e ensaiar a demonstração para 06/12/2026.

## Referências

Documentos do grupo: Distribuição de Atividades Atualizada, pp. 1-3; Arquitetura Atualizada, pp. 2-6; Plano de Execução dos Testes, pp. 1-3; Especificação de Publicação e Roadmap Revisada, pp. 1-2.

Referências técnicas: documentação oficial de Docker Compose, FastAPI, Vite e Scikit-learn. Links completos e análise de consistência em docs/ANALISE_DOCUMENTOS.md. Consulta em 18/11/2026.
