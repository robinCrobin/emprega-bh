/** Cálculos puros do gráfico de linha (sem DOM), usados por GraficoSerie e testados à parte. */

const MARGEM_PADRAO = { topo: 28, direita: 28, base: 36, esquerda: 48 };
const LARGURA_ROTULO_X = 56; // px reservados por rótulo de trimestre (ex.: "2024-T1")

/** Escala vertical começando em zero, com topo e marcações em números "redondos". */
export function escalaY(maximo, marcacoes = 4) {
  const max = Math.max(maximo, 1);
  const bruto = max / marcacoes;
  const potencia = Math.max(1, 10 ** Math.floor(Math.log10(bruto)));
  const fracao = bruto / potencia;
  const passo = (fracao <= 1 ? 1 : fracao <= 2 ? 2 : fracao <= 5 ? 5 : 10) * potencia;
  const topo = Math.ceil(max / passo) * passo;
  const valores = [];
  for (let v = 0; v <= topo; v += passo) valores.push(v);
  return { topo, passo, valores };
}

/** A cada quantos pontos mostrar o rótulo, contando de trás para frente (o último sempre aparece). */
export function passoDosRotulos(quantidade, larguraUtil) {
  if (quantidade <= 1) return 1;
  const larguraPorPonto = larguraUtil / (quantidade - 1);
  return Math.max(1, Math.ceil(LARGURA_ROTULO_X / larguraPorPonto));
}

const caminho = (pontos) => pontos.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

/**
 * Posiciona a série histórica e, se existir, o ponto da previsão (um trimestre após o último).
 * @param {{periodo: string, quantidade_vagas: number}[]} serie em ordem cronológica
 * @param {{trimestre_alvo: string, quantidade_estimada: number}|null} previsao
 */
export function montarGrafico({ serie, previsao = null, largura, altura, margem = MARGEM_PADRAO }) {
  const area = {
    esquerda: margem.esquerda, direita: largura - margem.direita,
    topo: margem.topo, base: altura - margem.base,
  };
  const categorias = serie.map((p) => p.periodo);
  if (previsao) categorias.push(previsao.trimestre_alvo);

  const valores = serie.map((p) => p.quantidade_vagas);
  if (previsao) valores.push(previsao.quantidade_estimada);
  const escala = escalaY(Math.max(0, ...valores));

  const larguraUtil = area.direita - area.esquerda;
  const posicaoX = (i) => (categorias.length === 1 ? area.esquerda + larguraUtil / 2
    : area.esquerda + (i * larguraUtil) / (categorias.length - 1));
  const posicaoY = (valor) => area.base - (valor / escala.topo) * (area.base - area.topo);

  const historico = serie.map((p, i) => ({
    periodo: p.periodo, valor: p.quantidade_vagas, x: posicaoX(i), y: posicaoY(p.quantidade_vagas),
  }));
  const estimativa = previsao ? {
    periodo: previsao.trimestre_alvo, valor: previsao.quantidade_estimada,
    x: posicaoX(categorias.length - 1), y: posicaoY(previsao.quantidade_estimada),
  } : null;

  const passo = passoDosRotulos(categorias.length, larguraUtil);
  const marcacoesX = categorias
    .map((periodo, i) => ({ periodo, x: posicaoX(i), indice: i }))
    .filter(({ indice }) => (categorias.length - 1 - indice) % passo === 0);

  return {
    largura, altura, area, escala,
    historico,
    estimativa,
    linhaHistorico: caminho(historico),
    linhaEstimativa: estimativa && historico.length ? caminho([historico.at(-1), estimativa]) : null,
    marcacoesY: escala.valores.map((valor) => ({ valor, y: posicaoY(valor) })),
    marcacoesX,
    // O rótulo da estimativa vai abaixo do ponto quando não sobra espaço acima.
    rotuloEstimativaAbaixo: estimativa ? estimativa.y - 12 < area.topo - 8 : false,
  };
}
