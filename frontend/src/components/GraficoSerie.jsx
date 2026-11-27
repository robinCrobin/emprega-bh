import { useEffect, useMemo, useRef, useState } from 'react';
import { montarGrafico } from '../lib/grafico.js';
import { formatarVagas } from '../lib/formato.js';

const LARGURA_INICIAL = 640;

/** Largura real do contêiner, para desenhar o gráfico em tamanho natural (texto legível no celular). */
function useLargura(referencia) {
  const [largura, setLargura] = useState(LARGURA_INICIAL);
  useEffect(() => {
    const elemento = referencia.current;
    if (!elemento) return undefined;
    const atualizar = () => setLargura(Math.max(Math.round(elemento.clientWidth), 280) || LARGURA_INICIAL);
    atualizar();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observador = new ResizeObserver(atualizar);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [referencia]);
  return largura;
}

/** Gráfico de linha (SVG) do histórico trimestral, com o ponto da estimativa em destaque tracejado. */
export default function GraficoSerie({ serie, previsao, descricao }) {
  const conteiner = useRef(null);
  const largura = useLargura(conteiner);
  const altura = Math.min(340, Math.max(220, Math.round(largura * 0.5)));
  const grafico = useMemo(
    () => montarGrafico({ serie, previsao, largura, altura }),
    [serie, previsao, largura, altura],
  );
  const { area, estimativa } = grafico;

  return (
    <div className="grafico" ref={conteiner}>
      <ul className="legenda" aria-hidden="true">
        <li><span className="legenda-linha" /> Vagas ofertadas</li>
        {estimativa && <li><span className="legenda-linha estimativa" /> Estimativa</li>}
      </ul>
      <svg
        width={largura}
        height={altura}
        viewBox={`0 0 ${largura} ${altura}`}
        role="img"
        aria-label={descricao}
      >
        {grafico.marcacoesY.map(({ valor, y }) => (
          <g key={valor}>
            <line className="grade" x1={area.esquerda} x2={area.direita} y1={y} y2={y} />
            <text className="rotulo" x={area.esquerda - 8} y={y} textAnchor="end" dominantBaseline="middle">
              {formatarVagas(valor)}
            </text>
          </g>
        ))}
        {grafico.marcacoesX.map(({ periodo, x }) => (
          <text key={periodo} className="rotulo" x={x} y={area.base + 20} textAnchor="middle">{periodo}</text>
        ))}

        <path className="linha-historico" d={grafico.linhaHistorico} />
        {grafico.linhaEstimativa && <path className="linha-estimativa" d={grafico.linhaEstimativa} />}

        {grafico.historico.map((ponto) => (
          <circle key={ponto.periodo} className="ponto" cx={ponto.x} cy={ponto.y} r="3">
            <title>{`${ponto.periodo}: ${formatarVagas(ponto.valor)} vagas`}</title>
          </circle>
        ))}
        {estimativa && (
          <g>
            <circle className="ponto-estimativa" cx={estimativa.x} cy={estimativa.y} r="5">
              <title>{`${estimativa.periodo}: estimativa de ${formatarVagas(estimativa.valor)} vagas`}</title>
            </circle>
            <text
              className="rotulo-estimativa"
              x={estimativa.x + 4}
              y={grafico.rotuloEstimativaAbaixo ? estimativa.y + 20 : estimativa.y - 12}
              textAnchor="end"
            >
              Estimativa: {formatarVagas(estimativa.valor)}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
