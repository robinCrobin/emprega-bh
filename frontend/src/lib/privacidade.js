/**
 * Privacidade (A17): a interface só aceita os campos do contrato (docs/API_CONTRATO.md).
 * Qualquer campo fora da lista (ex.: CNPJ, identificador de vaga, empresa) é descartado antes
 * de chegar ao estado da tela, e textos com cara de documento pessoal são mascarados.
 * As funções devolvem só os CAMINHOS dos campos descartados, nunca os valores.
 */

const OCUPACAO = { id: true, nome: true, codigo_cbo: true };
const JANELA = { inicio: true, fim: true };

const ESQUEMA_BUSCA = {
  termo: true,
  total_retornado: true,
  resultados: [OCUPACAO],
};

const ESQUEMA_SERIE = {
  ocupacao: OCUPACAO,
  total_trimestres: true,
  serie: [{ periodo: true, ano: true, trimestre: true, quantidade_vagas: true }],
  tendencia: {
    disponivel: true, classificacao: true, variacao_percentual: true,
    soma_recente: true, soma_anterior: true,
    periodo_recente: JANELA, periodo_anterior: JANELA,
    frase: true, motivo: true,
  },
  historico_suficiente: true,
  minimo_trimestres: true,
  previsao: { trimestre_alvo: true, quantidade_estimada: true, algoritmo: true },
  motivo_sem_previsao: true,
  aviso: true,
  informacoes_usadas: [{ chave: true, descricao: true }],
};

export const MASCARA = '[removido]';

// CNPJ (formatado ou 14 dígitos seguidos), CPF formatado e e-mail.
const PADROES_PESSOAIS = [
  /\b\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}\b/,
  /\b\d{14}\b/,
  /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/,
  /[\w.+-]+@[\w-]+\.[\w.-]+/,
];

export function contemDocumentoPessoal(texto) {
  return PADROES_PESSOAIS.some((padrao) => padrao.test(texto));
}

const ehObjeto = (valor) => valor !== null && typeof valor === 'object' && !Array.isArray(valor);

function filtrar(valor, esquema, caminho, descartados) {
  if (esquema === true) {
    if (valor !== null && typeof valor === 'object') {
      descartados.push(caminho);
      return null;
    }
    if (typeof valor === 'string' && contemDocumentoPessoal(valor)) {
      descartados.push(caminho);
      return MASCARA;
    }
    return valor;
  }
  if (Array.isArray(esquema)) {
    if (!Array.isArray(valor)) {
      if (valor != null) descartados.push(caminho);
      return [];
    }
    return valor.map((item) => filtrar(item, esquema[0], `${caminho}[]`, descartados));
  }
  if (!ehObjeto(valor)) {
    if (valor != null) descartados.push(caminho);
    return null;
  }
  const limpo = {};
  for (const [chave, conteudo] of Object.entries(valor)) {
    const destino = caminho ? `${caminho}.${chave}` : chave;
    if (Object.hasOwn(esquema, chave)) limpo[chave] = filtrar(conteudo, esquema[chave], destino, descartados);
    else descartados.push(destino);
  }
  return limpo;
}

function aplicar(resposta, esquema) {
  const descartados = [];
  const dados = filtrar(resposta, esquema, '', descartados);
  return { dados, descartados };
}

/** Resposta de GET /ocupacoes. */
export const sanitizarBusca = (resposta) => aplicar(resposta, ESQUEMA_BUSCA);

/** Resposta de GET /ocupacoes/{id}/serie. */
export const sanitizarSerie = (resposta) => aplicar(resposta, ESQUEMA_SERIE);
