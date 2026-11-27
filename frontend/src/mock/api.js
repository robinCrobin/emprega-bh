/**
 * Implementação em memória dos endpoints de ocupações, com o mesmo formato e as mesmas
 * regras de docs/API_CONTRATO.md. Sem dependência do navegador, para poder ser testada.
 */
import { ErroApi } from '../erroApi.js';
import { AVISO_ESTIMATIVA, INFORMACOES_USADAS, OCUPACOES } from './dados.js';

export const MINIMO_TRIMESTRES = 8;
const LIMITE_PADRAO = 20;
const LIMITE_MAXIMO = 50;
const JANELA = 4;

export function normalizar(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

const rotulo = (ano, trimestre) => `${ano}-T${trimestre}`;

function cancelamento() {
  return new DOMException('Requisição cancelada.', 'AbortError');
}

function aguardar(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(cancelamento()); return; }
    const espera = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => { clearTimeout(espera); reject(cancelamento()); }, { once: true });
  });
}

function resumo({ id, nome, codigo_cbo }) {
  return { id, nome, codigo_cbo };
}

function calcularTendencia(serie) {
  const vazia = {
    disponivel: false, classificacao: null, variacao_percentual: null, soma_recente: null,
    soma_anterior: null, periodo_recente: null, periodo_anterior: null, frase: null, motivo: null,
  };
  if (serie.length < Math.max(MINIMO_TRIMESTRES, 2 * JANELA)) {
    return {
      ...vazia,
      motivo: `Tendência indisponível: a ocupação tem ${serie.length} trimestre(s) com dados e são `
        + `necessários pelo menos ${Math.max(MINIMO_TRIMESTRES, 2 * JANELA)} para comparar os últimos 4 `
        + 'trimestres com os 4 anteriores.',
    };
  }
  const recente = serie.slice(-JANELA);
  const anterior = serie.slice(-2 * JANELA, -JANELA);
  const soma = (pontos) => pontos.reduce((total, p) => total + p.quantidade_vagas, 0);
  const somaRecente = soma(recente);
  const somaAnterior = soma(anterior);
  const janela = (pontos) => ({
    inicio: rotulo(pontos[0].ano, pontos[0].trimestre),
    fim: rotulo(pontos.at(-1).ano, pontos.at(-1).trimestre),
  });
  if (somaAnterior === 0) {
    return {
      ...vazia,
      motivo: 'Tendência indisponível: não houve vagas nos 4 trimestres anteriores, '
        + 'então a variação percentual não pode ser calculada.',
    };
  }
  const variacao = (100 * (somaRecente - somaAnterior)) / somaAnterior;
  const [classificacao, descricao] = variacao > 10 ? ['crescente', 'estão crescendo']
    : variacao < -10 ? ['decrescente', 'estão diminuindo'] : ['estável', 'estão estáveis'];
  return {
    disponivel: true, classificacao, variacao_percentual: Math.round(variacao * 10) / 10,
    soma_recente: somaRecente, soma_anterior: somaAnterior,
    periodo_recente: janela(recente), periodo_anterior: janela(anterior),
    frase: `As vagas desta ocupação ${descricao}: foram ${somaRecente} nos últimos 4 trimestres com dados, `
      + `contra ${somaAnterior} nos 4 anteriores (${variacao >= 0 ? '+' : ''}${variacao.toFixed(1)}%).`,
    motivo: null,
  };
}

/** GET /ocupacoes?q=&limit= */
export async function buscarOcupacoesMock(q, { limit = LIMITE_PADRAO, signal, atrasoMs = 250 } = {}) {
  await aguardar(atrasoMs, signal);
  const termo = typeof q === 'string' ? q.trim() : '';
  if (termo.length < 2 || termo.length > 100) throw new ErroApi(422, 'Parâmetros inválidos: q.');
  const palavras = normalizar(termo).split(/\s+/);
  const teto = Math.min(limit, LIMITE_MAXIMO);
  const resultados = OCUPACOES
    .filter((o) => palavras.every((palavra) => normalizar(o.nome).includes(palavra)))
    .slice(0, teto)
    .map(resumo);
  return { termo: q, total_retornado: resultados.length, resultados };
}

/** GET /ocupacoes/{id}/serie */
export async function obterSerieMock(id, { signal, atrasoMs = 250 } = {}) {
  await aguardar(atrasoMs, signal);
  const ocupacao = OCUPACOES.find((o) => o.id === Number(id));
  if (!ocupacao) throw new ErroApi(404, 'Ocupação não encontrada.');
  const serie = ocupacao.serie.map((p) => ({
    periodo: rotulo(p.ano, p.trimestre), ano: p.ano, trimestre: p.trimestre,
    quantidade_vagas: p.quantidade_vagas,
  }));
  const suficiente = serie.length >= MINIMO_TRIMESTRES;
  const ultimo = ocupacao.serie.at(-1);
  const alvo = ultimo.trimestre === 4 ? rotulo(ultimo.ano + 1, 1) : rotulo(ultimo.ano, ultimo.trimestre + 1);
  let previsao = null;
  let motivo = null;
  if (!suficiente) {
    motivo = `Esta ocupação tem ${serie.length} trimestre(s) com dados e o mínimo para gerar previsão é `
      + `${MINIMO_TRIMESTRES}. Exibimos apenas o histórico disponível.`;
  } else if (ocupacao.previsao) {
    previsao = { trimestre_alvo: alvo, ...ocupacao.previsao };
  } else {
    motivo = `A previsão para ${alvo} ainda não foi gerada para esta ocupação.`;
  }
  return {
    ocupacao: resumo(ocupacao),
    total_trimestres: serie.length,
    serie,
    tendencia: calcularTendencia(ocupacao.serie),
    historico_suficiente: suficiente,
    minimo_trimestres: MINIMO_TRIMESTRES,
    previsao,
    motivo_sem_previsao: motivo,
    aviso: AVISO_ESTIMATIVA,
    informacoes_usadas: previsao ? INFORMACOES_USADAS : [],
  };
}
