# Plano de integracao e verificacao

Sthel coordena os testes integrados, com apoio das frentes. Os testes unitarios
de dados, modelo, API de negocio e interface sao responsabilidade de quem os
implementa. Cada integrante entrega comandos, resultado, versao e evidencias.

## Preparacao

1. Fixar commit, versoes de dependencias, origem e hash da base, data de coleta
   e artefato do modelo. Registrar hardware e ambiente da demonstracao.
2. Acordar nomes dos campos, contratos dos endpoints e identificador de ocupacao.
   Os documentos atuais nao trazem contratos completos; Nicolas consolida com
   Joao Pedro, Roberta e Davi antes de automatizar os testes funcionais.
3. Preparar banco isolado com ocupacoes de historico suficiente (8 ou mais),
   insuficiente (0 a 7) e casos de borda. Usar dados controlados identificados
   como fixtures, sem confundi-los com dados reais da PBH.
4. Executar os testes de cada frente, instalar o sistema e validar o smoke.
5. Executar integracao, fluxo ponta a ponta e verificacoes nao funcionais;
   registrar cada caso em matriz_testes.csv com evidencia e defeito associado.

## Casos obrigatorios

A matriz CSV descreve os cenarios, preparacao, resultado esperado, apoio e estado.
Os IDs CT-INT-01 a 04 preservam o plano enviado pelo grupo. CT-UI-01 a 04
tambem preservam os IDs originais; foram acrescentados casos complementares.
Todos os casos funcionais comecam como Nao executado.

## Regras e bordas

- Buscar por parte do nome, acentos e caixa. Comparar IDs retornados, nao apenas
  o texto apresentado. Consulta sem resultado mostra mensagem compreensivel.
- Historico ordenado cronologicamente, com quantidades iguais as da carga de
  referencia; proximo trimestre e calculado a partir do ultimo periodo valido.
- Menos de oito trimestres validos: previsao null e motivo; nao executar
  inferencia. Testar 7 e 8 separadamente. O minimo e condicao necessaria;
  disponibilidade de um modelo avaliado tambem precisa ser verificada.
- Tendencia: soma recente R dos ultimos quatro trimestres e soma anterior B dos
  quatro anteriores; com B > 0, variacao = 100 * (R - B) / B. Valores > +10%
  sao crescentes, < -10% decrescentes e os limites exatos sao estaveis.
- Para B = 0 ou historico com menos de oito trimestres, nao dividir por zero nem
  inventar percentual. Proposta: tendencia indisponivel com motivo. O grupo
  precisa confirmar a apresentacao desse caso antes de transforma-lo em aceite.
- Nao preencher automaticamente trimestre sem registro com zero. Roberta deve
  distinguir ausencia de oferta de ausencia de cobertura da fonte.
- A API consulta historico e previsoes persistidos, conforme a arquitetura.
  A consulta do usuario nao deve refazer coleta CKAN ou treinamento.
- Aviso de estimativa deve estar visivel na mesma tela do resultado. Verificar
  interface, DOM e payloads contra uma lista de campos permitidos, evitando
  CNPJ e identificadores individuais de vaga. ID de ocupacao e permitido.

## Avaliacao do modelo

Davi entrega a divisao temporal, quantidade de exemplos de treino e teste,
algoritmo, parametros, semente, periodos e metricas MAE/RMSE. Nenhum embaralhamento
temporal e permitido. Se houver ajuste de hiperparametros, usar validacao dentro
do treino ou backtesting; reservar o teste final para a avaliacao final.

Proposta para tornar o aceite mensuravel: comparar MAE e RMSE com uma previsao
de referencia pela media dos quatro trimestres anteriores, nos mesmos periodos
e com informacao disponivel na data de cada previsao. O grupo deve aprovar esse
criterio antes da execucao. Se o modelo nao superar a referencia, registrar o
resultado e revisar; nao afirmar ganho ou estabilidade estatistica sem evidencia.

## Nao funcionais

- Instalar em copia nova com .env gerado, mantendo os locks, sem depender de
  arquivos privados da maquina de outro integrante.
- Testar larguras de 375, 768 e 1366 px; verificar scroll horizontal, grafico,
  aviso, foco de teclado e mensagens. Essas larguras sao a grade proposta de teste.
- Contar acoes de entrada e selecao da consulta principal, definindo a unidade
  como foco, digitacao do termo (uma acao) e selecao. Buscar concluir em ate tres
  interacoes; registrar o criterio usado com o grupo.
- Medir HTTP e tempo ate grafico/resultado visivel separadamente. Registrar a
  primeira consulta e 30 consultas aquecidas ao endpoint funcional. A meta de
  ate 3 s sera verificada no ambiente de demonstracao e na tela, nao apenas no
  /healthz. API adormecida em hospedagem gratuita deve ter comportamento
  documentado e validacao separada, sem ocultar a primeira latencia.

Para medir HTTP, substituir a URL abaixo pelo endpoint funcional real:

```sh
python scripts/measure_latency.py --url http://127.0.0.1:8000/ENDPOINT_REAL --samples 30
```

O script falha diante de erro HTTP, timeout ou qualquer amostra aquecida acima
do limite. Guarda media, p95, maximo e primeira requisicao. Nao comprova tempo
visual nem qualidade da resposta; esses pontos sao registrados nos testes de UI.

## Aceite e evidencias

Todos os casos obrigatorios precisam ter resultado e evidencia. Defeitos de
regra de negocio, vazamento temporal, previsao sem historico minimo, exposicao
indevida e falhas que impedem a jornada precisam ser corrigidos antes da entrega.
Nao marcar Bloqueado ou Nao executado como Aprovado. A consolidacao registra
limitacoes, falhas, versao final e resultado das metricas; cobertura pode apoiar
a analise, mas nao substitui a execucao dos cenarios.
