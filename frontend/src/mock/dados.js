/**
 * DADOS FICTÍCIOS para desenvolvimento da interface (A14/A15). Não são dados da PBH.
 * Os formatos seguem docs/API_CONTRATO.md; ids e códigos CBO (9991xx) seguem o seed do banco.
 */

export const AVISO_ESTIMATIVA =
  'Esta previsão é uma estimativa gerada por inteligência artificial a partir de dados '
  + 'históricos. Ela não garante a existência de vagas nem de emprego e não é uma '
  + 'recomendação profissional.';

export const INFORMACOES_USADAS = [
  { chave: 'historico', descricao: 'Quantidade de vagas da ocupação nos 4 trimestres anteriores ao previsto.' },
  { chave: 'sazonalidade', descricao: 'Trimestre do ano (1 a 4), para considerar épocas de mais ou menos contratação.' },
  { chave: 'tendencia_recente', descricao: 'Comportamento recente das vagas da ocupação, comparando trimestres próximos.' },
];

/** Trimestres consecutivos a partir de `anoInicial`-T1. */
function trimestres(anoInicial, valores) {
  return valores.map((quantidade, i) => ({
    ano: anoInicial + Math.floor(i / 4),
    trimestre: (i % 4) + 1,
    quantidade_vagas: quantidade,
  }));
}

export const OCUPACOES = [
  {
    id: 1, nome: 'Analista de sistemas', codigo_cbo: '999101',
    // 24 trimestres, crescente, com previsão gravada.
    serie: trimestres(2021, [60, 60, 67, 70, 76, 76, 79, 89, 89, 94, 92, 96, 103, 106, 109, 118,
      117, 125, 124, 132, 130, 138, 141, 147]),
    previsao: { quantidade_estimada: 150.4, algoritmo: 'regressao_linear' },
  },
  {
    id: 2, nome: 'Auxiliar administrativo', codigo_cbo: '999102',
    // 7 trimestres: histórico insuficiente, sem previsão.
    serie: trimestres(2025, [30, 28, 33, 29, 31, 27, 30]),
    previsao: null,
  },
  {
    id: 3, nome: 'Técnico em enfermagem', codigo_cbo: '999103',
    // Exatamente 8 trimestres (fronteira do mínimo), com previsão.
    serie: trimestres(2025, [40, 44, 42, 48, 51, 49, 55, 58]),
    previsao: { quantidade_estimada: 56.6, algoritmo: 'regressao_linear' },
  },
  {
    id: 4, nome: 'Vendedor', codigo_cbo: '999104',
    // 16 trimestres, histórico suficiente, mas previsão ainda não gerada.
    serie: trimestres(2023, [80, 85, 78, 90, 88, 92, 86, 95, 91, 97, 93, 99, 94, 98, 96, 101]),
    previsao: null,
  },
  {
    id: 5, nome: 'Motorista', codigo_cbo: '999105',
    // 12 trimestres, decrescente, com previsão.
    serie: trimestres(2024, [70, 68, 66, 63, 60, 58, 55, 52, 50, 47, 45, 42]),
    previsao: { quantidade_estimada: 40.5, algoritmo: 'random_forest' },
  },
  {
    id: 6, nome: 'Técnico em informática', codigo_cbo: '999106',
    // 9 trimestres, estável, com previsão.
    serie: trimestres(2024, [22, 24, 21, 25, 23, 26, 24, 27, 25]),
    previsao: { quantidade_estimada: 26, algoritmo: 'regressao_linear' },
  },
  {
    id: 7, nome: 'Operador de empilhadeira', codigo_cbo: '999107',
    // 8 trimestres com os 4 primeiros zerados: base anterior zero, tendência indisponível.
    serie: trimestres(2025, [0, 0, 0, 0, 12, 15, 14, 18]),
    previsao: null,
  },
];
