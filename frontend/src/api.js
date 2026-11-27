/**
 * Acesso aos endpoints de ocupações (docs/API_CONTRATO.md).
 *
 * Enquanto VITE_USE_MOCK não for "false", usa os dados fictícios de src/mock. Para usar a
 * API real: VITE_USE_MOCK=false (o navegador acessa a API pelo proxy /api do Vite).
 */
import { ErroApi } from './erroApi.js';
import { sanitizarBusca, sanitizarSerie } from './lib/privacidade.js';
import { buscarOcupacoesMock, obterSerieMock } from './mock/api.js';

const USAR_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';
const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function requisitar(caminho, parametros, signal) {
  const consulta = parametros ? `?${new URLSearchParams(parametros)}` : '';
  let resposta;
  try {
    resposta = await fetch(`${BASE}${caminho}${consulta}`, {
      signal,
      headers: { Accept: 'application/json' },
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
    });
  } catch (erro) {
    if (erro.name === 'AbortError') throw erro;
    throw new ErroApi(0, 'Não foi possível conectar ao serviço. Tente novamente em instantes.');
  }
  if (!resposta.ok) {
    let detalhe = null;
    try { detalhe = (await resposta.json()).detail; } catch { /* corpo sem JSON */ }
    throw new ErroApi(resposta.status, detalhe || 'Erro inesperado ao consultar o serviço.');
  }
  return resposta.json();
}

export const usandoMock = USAR_MOCK;

/** Mantém só os campos do contrato (A17); avisa no console de desenvolvimento quais foram descartados. */
function aplicarPrivacidade({ dados, descartados }) {
  if (descartados.length > 0 && import.meta.env.DEV) {
    console.warn('Campos fora do contrato da API foram descartados:', descartados.join(', '));
  }
  return dados;
}

/** Busca ocupações pelo nome (RF01). */
export async function buscarOcupacoes(termo, signal) {
  const resposta = USAR_MOCK
    ? await buscarOcupacoesMock(termo, { signal })
    : await requisitar('/ocupacoes', { q: termo }, signal);
  return aplicarPrivacidade(sanitizarBusca(resposta));
}

/** Série histórica e previsão de uma ocupação (RF02, RF04). */
export async function obterSerie(id, signal) {
  const resposta = USAR_MOCK
    ? await obterSerieMock(id, { signal })
    : await requisitar(`/ocupacoes/${encodeURIComponent(id)}/serie`, null, signal);
  return aplicarPrivacidade(sanitizarSerie(resposta));
}
