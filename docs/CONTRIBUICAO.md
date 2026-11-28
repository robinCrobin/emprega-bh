# Organizacao e colaboracao

Responsavel pela base e consolidacao: Sthel Felipe Torres.

## Frentes e diretorios

| Diretorio | Responsabilidade |
| --- | --- |
| pipeline, data | Roberta: coleta e tratamento; Davi: dados do modelo |
| modelagem, models | Davi: codigo de treino e avaliacao em modelagem; artefatos binarios em models (fora do Git) |
| database, backend | Nicolas: esquema, carga e API |
| frontend | Joao Pedro: interface React |
| scripts, docs, tests, .github | Sthel: ambiente, integracao e consolidacao |

Os caminhos sao a proposta inicial para desenvolvimento paralelo. Nao ha
implementacao das partes dos colegas neste pacote.

## Fluxo Git

main deve conter a versao integrada. Criar branches curtas por atividade:
feat/a04-coleta-ckan, feat/a09-api, test/a19-integracao ou docs/a21-execucao.
Abrir pull request com ID da atividade, descricao e evidencias. Integrar depois
das verificacoes e da revisao por outro integrante quando disponivel. Protecao
de branch precisa ser configurada na plataforma do repositorio.

Para iniciar um repositorio novo, executar git init -b main, revisar git status
e configurar o remoto real do grupo. Se ja houver repositorio, incorporar esta
estrutura em uma branch, preservando o codigo existente. Nao criar repositorio
duplicado nem substituir arquivos existentes sem revisar os diffs.

## Dependencias e dados

Versionar requirements.in e requirements.txt com hashes, alem de package.json
e package-lock.json. Instalar Python com pip --require-hashes e frontend com
npm ci. Gerar novamente o lock quando alterar dependencias. Dados brutos,
dados tratados locais, modelos binarios e .env ficam fora do Git; registrar
origem, data da coleta, versao, hash dos dados e semente em um manifesto sem
credenciais. Davi fixa random_state onde aplicavel.

As imagens Docker sao fixadas por digest no compose e nos Dockerfiles deste
pacote. Qualquer atualizacao deve revisar tags, digests e repetir o smoke.
