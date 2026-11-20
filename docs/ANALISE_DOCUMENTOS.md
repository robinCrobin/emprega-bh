# Analise de consistencia dos documentos

O escopo e viavel para uma primeira versao academica: Python e Pandas no
pipeline, Scikit-learn na regressao, PostgreSQL, FastAPI e React. A distribuicao
das frentes permite desenvolvimento paralelo. A contribuicao de Sthel abrange
A01, A02, coordenacao da A18, A19, A20 e A21. O print do grupo destaca a
preparacao inicial; a distribuicao tambem atribui a Sthel a consolidacao final.

## Criterios do modelo

O plano de testes compara MAE a variancia natural. MAE tem unidade vagas e a
variancia tem unidade vagas ao quadrado; a comparacao direta nao e adequada.
Propor comparar MAE e RMSE a uma referencia de media movel de quatro trimestres
nos mesmos cortes temporais. Registrar ambos, sem declarar significancia ou
estabilidade estatistica a partir de uma unica avaliacao pequena.

O minimo de oito trimestres foi preservado. Com quatro defasagens, oito pontos
produzem somente quatro exemplos supervisionados completos. Reservar o ultimo
ano inteiro para teste deixaria zero exemplos para treino nesse caso. Davi
precisa ajustar o corte ao numero de exemplos apos as defasagens e registrar a
limitacao; um corte 3/1 teria treino e teste, mas seria muito fraco para alegar
estabilidade. Series maiores permitem avaliacao temporal mais informativa.

O plano fala em comparar algoritmos sobre o teste. Para que o teste final
continue independente, selecionar algoritmo e parametros usando validacao
temporal dentro do treino; avaliar a escolha final no teste reservado.

## Regras a alinhar na integracao

- API e previsoes: a arquitetura preve resultados pre-calculados no banco.
  Seguir essa estrategia em vez de treinar ou coletar a cada consulta, mesmo
  quando o plano de testes menciona genericamente acionar o modelo pela API.
- Tendencia: incluir decrescente, limites exatos de +/-10% e caso B=0. A forma
  de mostrar tendencia indisponivel deve ser confirmada pelo grupo.
- Historico: distinguir lacunas de cobertura de zero vagas e definir se o ultimo
  trimestre esta fechado antes de compor a serie usada no modelo.
- Desempenho: a meta de 3 s precisa identificar o ambiente e incluir verificacao
  visual; suspensao de provedor gratuito nao pode ficar escondida no resultado.
- Privacidade: conferir payloads da API alem do DOM; permitir ID de ocupacao,
  excluindo CNPJ e identificadores individuais de vaga dos dados apresentados.

Estas observacoes nao alteram os PDFs originais nem implementam as frentes dos
colegas. Sao orientacoes de integracao e propostas de criterios para o grupo.

## Referencias do projeto

1. EmpregaBH_Distribuicao_Atividades_Atualizada (1).pdf, pp. 1-3.
2. Arquitetura_EmpregaBH_Atualizada.pdf, pp. 3-6 e diagrama da p. 2.
3. Plano de Execucao dos Testes - EmpregaBH.pdf, pp. 1-3.
4. EmpregaBH_Especificacao_Publicacao_Roadmap_Revisada.pdf, pp. 1-2.

## Referencias tecnicas consultadas

- https://docs.docker.com/compose/how-tos/startup-order/
- https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/
- https://fastapi.tiangolo.com/deployment/docker/
- https://vite.dev/guide/
- https://scikit-learn.org/stable/modules/cross_validation.html
- https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html
- https://scikit-learn.org/stable/modules/generated/sklearn.metrics.root_mean_squared_error.html

Consulta em 18/11/2026. As plataformas Vercel, Render e Neon seguem como a
proposta do grupo; publicacao e condicoes de planos nao foram validadas nesta etapa.
