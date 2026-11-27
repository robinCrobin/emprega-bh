/** Formatação de textos exibidos na interface. */

const ALGORITMOS = {
  regressao_linear: 'Regressão linear',
  random_forest: 'Random Forest',
};

/** Vagas são contagens: a estimativa é exibida arredondada, com separador de milhar. */
export function formatarVagas(valor) {
  return Math.round(valor).toLocaleString('pt-BR');
}

/** Variação com sinal e uma casa decimal: +22,4% / −8,0% / 0,0%. */
export function formatarVariacao(percentual) {
  const numero = Math.abs(percentual).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (percentual > 0) return `+${numero}%`;
  if (percentual < 0) return `−${numero}%`;
  return `${numero}%`;
}

const TENDENCIAS = {
  crescente: { texto: 'Crescente', simbolo: '▲', classe: 'crescente' },
  decrescente: { texto: 'Decrescente', simbolo: '▼', classe: 'decrescente' },
  estável: { texto: 'Estável', simbolo: '■', classe: 'estavel' },
};

/** Texto, símbolo e classe visual da classificação (o símbolo evita depender só da cor). */
export function descreverTendencia(classificacao) {
  return TENDENCIAS[classificacao] || { texto: classificacao, simbolo: '■', classe: 'estavel' };
}

export function formatarAlgoritmo(chave) {
  return ALGORITMOS[chave] || chave.replace(/_/g, ' ');
}
