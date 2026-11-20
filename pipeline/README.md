# Frente de dados e modelo

Roberta implementa a coleta CKAN, limpeza e agregacao. Davi implementa treino,
avaliacao e previsao. Os modulos desta frente devem ter importacoes sem efeitos
colaterais e comandos explicitos para executar coleta/treino.

Criar requirements.in com as versoes escolhidas de Pandas, Scikit-learn e demais
dependencias, e gerar o respectivo lock antes da integracao. Nao ha coleta ou
modelo implementado neste pacote de infraestrutura. Nenhum dado e metrica foi
simulado como se fosse real.
