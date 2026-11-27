import { descreverTendencia, formatarVariacao } from '../lib/formato.js';

/** Tendência recente (A16): últimos 4 trimestres contra os 4 anteriores, ou o motivo de não haver. */
export default function Tendencia({ tendencia }) {
  if (!tendencia) return null;

  if (!tendencia.disponivel) {
    return (
      <section className="tendencia tendencia-indisponivel" aria-labelledby="titulo-tendencia">
        <h3 id="titulo-tendencia">Tendência recente</h3>
        <p>{tendencia.motivo}</p>
      </section>
    );
  }

  const { texto, simbolo, classe } = descreverTendencia(tendencia.classificacao);
  const { periodo_recente: recente, periodo_anterior: anterior } = tendencia;
  return (
    <section className="tendencia" aria-labelledby="titulo-tendencia">
      <h3 id="titulo-tendencia">Tendência recente</h3>
      <p className="tendencia-resumo">
        <span className={`selo selo-${classe}`}>
          <span aria-hidden="true">{simbolo}</span> {texto}
        </span>
        <strong className="tendencia-variacao">{formatarVariacao(tendencia.variacao_percentual)}</strong>
      </p>
      <p>{tendencia.frase}</p>
      {recente && anterior && (
        <p className="tendencia-janelas">
          Compara {recente.inicio} a {recente.fim} com {anterior.inicio} a {anterior.fim}.
        </p>
      )}
    </section>
  );
}
