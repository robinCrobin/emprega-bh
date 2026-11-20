# Frente PostgreSQL

Nicolas cria as migrations, tabelas e carga dos dados. A configuracao deste
pacote inicia um PostgreSQL vazio e permite verificar a conexao com SELECT 1.
O healthcheck nao comprova a existencia das tabelas do sistema.

Versionar scripts de esquema nesta pasta e documentar comandos de aplicacao.
Scripts em /docker-entrypoint-initdb.d so executam na criacao inicial do volume;
nao usar esse comportamento como substituto para migrations incrementais.
