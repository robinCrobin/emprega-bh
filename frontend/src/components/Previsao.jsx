import { formatarAlgoritmo, formatarVagas } from '../lib/formato.js';

// Usado só se a API não enviar o aviso; o texto da API (RF06) tem prioridade.
const AVISO_PADRAO =
  'Esta previsão é uma estimativa gerada por inteligência artificial a partir de dados históricos. '
  + 'Ela não garante a existência de vagas nem de emprego e não é uma recomendação profissional.';

/**
 * Estimativa do próximo trimestre (A16). O aviso fica no mesmo bloco do número, sempre visível,
 * para a estimativa nunca aparecer como garantia ou recomendação profissional.
 */
export default function Previsao({ previsao, motivo, aviso, informacoesUsadas }) {
  if (!previsao) {
    return (
      <section className="previsao sem-previsao" aria-labelledby="titulo-previsao">
        <h3 id="titulo-previsao">Estimativa não disponível</h3>
        <p>{motivo}</p>
      </section>
    );
  }

  return (
    <section className="previsao" aria-labelledby="titulo-previsao">
      <h3 id="titulo-previsao">Estimativa para {previsao.trimestre_alvo}</h3>
      <p className="previsao-valor">
        Cerca de <strong>{formatarVagas(previsao.quantidade_estimada)} vagas</strong>
        <span className="previsao-algoritmo"> ({formatarAlgoritmo(previsao.algoritmo)})</span>
      </p>
      <p className="aviso-estimativa" role="note">
        <strong>Atenção: é uma estimativa.</strong> {aviso || AVISO_PADRAO}
      </p>
      {informacoesUsadas?.length > 0 && (
        <details className="informacoes-usadas">
          <summary>O que embasa esta estimativa</summary>
          <ul>
            {informacoesUsadas.map((info) => <li key={info.chave}>{info.descricao}</li>)}
          </ul>
        </details>
      )}
    </section>
  );
}
