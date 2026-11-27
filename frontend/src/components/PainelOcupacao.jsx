import { useEffect, useRef, useState } from 'react';
import { obterSerie } from '../api.js';
import { formatarVagas } from '../lib/formato.js';
import GraficoSerie from './GraficoSerie.jsx';
import Previsao from './Previsao.jsx';
import Tendencia from './Tendencia.jsx';

/** Resultado da ocupação selecionada (A15): série histórica em gráfico e estimativa do próximo trimestre. */
export default function PainelOcupacao({ ocupacaoId }) {
  const [estado, setEstado] = useState({ status: 'ocioso', dados: null, mensagem: '' });
  const tituloRef = useRef(null);

  useEffect(() => {
    if (ocupacaoId == null) {
      setEstado({ status: 'ocioso', dados: null, mensagem: '' });
      return undefined;
    }
    const controlador = new AbortController();
    setEstado({ status: 'carregando', dados: null, mensagem: '' });
    obterSerie(ocupacaoId, controlador.signal)
      .then((dados) => setEstado({ status: 'pronto', dados, mensagem: '' }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return;
        setEstado({ status: 'erro', dados: null, mensagem: erro.message });
      });
    return () => controlador.abort();
  }, [ocupacaoId]);

  // Leva o foco ao resultado quando ele chega, para teclado e leitor de tela.
  useEffect(() => {
    if (estado.status === 'pronto') tituloRef.current?.focus();
  }, [estado.status, estado.dados]);

  const { status, dados, mensagem } = estado;

  if (status === 'ocioso') {
    return (
      <section className="painel painel-vazio" aria-labelledby="titulo-painel">
        <h2 id="titulo-painel">Resultado</h2>
        <p>Busque uma ocupação e selecione-a na lista para ver o histórico de vagas.</p>
      </section>
    );
  }
  if (status === 'carregando') {
    return (
      <section className="painel" aria-labelledby="titulo-painel" aria-busy="true">
        <h2 id="titulo-painel">Resultado</h2>
        <p role="status">Carregando histórico…</p>
      </section>
    );
  }
  if (status === 'erro') {
    return (
      <section className="painel" aria-labelledby="titulo-painel">
        <h2 id="titulo-painel">Resultado</h2>
        <p className="mensagem-erro" role="alert">{mensagem}</p>
      </section>
    );
  }

  const { ocupacao, serie, previsao, motivo_sem_previsao: motivo } = dados;
  const primeiro = serie[0]?.periodo;
  const ultimo = serie.at(-1)?.periodo;
  const descricao = `Gráfico de linha das vagas por trimestre de ${ocupacao.nome}, de ${primeiro} a ${ultimo}`
    + (previsao ? `, com estimativa de ${formatarVagas(previsao.quantidade_estimada)} vagas para ${previsao.trimestre_alvo}.` : '.');

  return (
    <section className="painel" aria-labelledby="titulo-painel">
      <header>
        <h2 id="titulo-painel" tabIndex={-1} ref={tituloRef}>{ocupacao.nome}</h2>
        <p className="painel-detalhe">
          {ocupacao.codigo_cbo && <>CBO {ocupacao.codigo_cbo} · </>}
          {dados.total_trimestres} trimestres com dados, de {primeiro} a {ultimo}
        </p>
      </header>

      <GraficoSerie serie={serie} previsao={previsao} descricao={descricao} />

      <Tendencia tendencia={dados.tendencia} />
      <Previsao
        previsao={previsao}
        motivo={motivo}
        aviso={dados.aviso}
        informacoesUsadas={dados.informacoes_usadas}
      />

      <details className="tabela-serie">
        <summary>Ver os dados em tabela</summary>
        <table>
          <caption className="somente-leitor">Vagas por trimestre de {ocupacao.nome}</caption>
          <thead><tr><th scope="col">Trimestre</th><th scope="col">Vagas</th></tr></thead>
          <tbody>
            {serie.map((ponto) => (
              <tr key={ponto.periodo}>
                <th scope="row">{ponto.periodo}</th>
                <td>{formatarVagas(ponto.quantidade_vagas)}</td>
              </tr>
            ))}
            {previsao && (
              <tr className="linha-estimativa">
                <th scope="row">{previsao.trimestre_alvo} (estimativa)</th>
                <td>≈ {formatarVagas(previsao.quantidade_estimada)}</td>
              </tr>
            )}
          </tbody>
        </table>
      </details>
    </section>
  );
}
