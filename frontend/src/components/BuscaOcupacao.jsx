import { useCallback, useEffect, useRef, useState } from 'react';
import { buscarOcupacoes } from '../api.js';

const MINIMO_CARACTERES = 2;
const ATRASO_DIGITACAO_MS = 300;

/** Busca por ocupação (A14): consulta enquanto o usuário digita e lista os resultados. */
export default function BuscaOcupacao({ selecionadoId, onSelecionar }) {
  const [termo, setTermo] = useState('');
  const [estado, setEstado] = useState({ status: 'ocioso', resultados: [], termo: '', mensagem: '' });
  const controladorRef = useRef(null);

  const buscar = useCallback(async (texto) => {
    controladorRef.current?.abort();
    const alvo = texto.trim();
    if (alvo.length < MINIMO_CARACTERES) {
      setEstado({ status: 'ocioso', resultados: [], termo: '', mensagem: '' });
      return;
    }
    const controlador = new AbortController();
    controladorRef.current = controlador;
    setEstado((atual) => ({ ...atual, status: 'carregando' }));
    try {
      const resposta = await buscarOcupacoes(alvo, controlador.signal);
      setEstado({ status: 'pronto', resultados: resposta.resultados, termo: alvo, mensagem: '' });
    } catch (erro) {
      if (erro.name === 'AbortError') return;
      setEstado({ status: 'erro', resultados: [], termo: alvo, mensagem: erro.message });
    }
  }, []);

  // Espera o usuário parar de digitar para não consultar a cada tecla.
  useEffect(() => {
    const espera = setTimeout(() => buscar(termo), ATRASO_DIGITACAO_MS);
    return () => clearTimeout(espera);
  }, [termo, buscar]);

  useEffect(() => () => controladorRef.current?.abort(), []);

  const { status, resultados, termo: termoConsultado, mensagem } = estado;
  const digitouPouco = termo.trim().length === 1;

  let aviso = null;
  if (digitouPouco) aviso = `Digite pelo menos ${MINIMO_CARACTERES} caracteres.`;
  else if (status === 'carregando') aviso = 'Buscando ocupações…';
  else if (status === 'pronto' && resultados.length === 0) {
    aviso = `Nenhuma ocupação encontrada para “${termoConsultado}”. Tente outro nome ou parte dele.`;
  } else if (status === 'pronto') {
    aviso = `${resultados.length} ${resultados.length === 1 ? 'ocupação encontrada' : 'ocupações encontradas'}.`;
  }

  return (
    <section className="busca" aria-labelledby="titulo-busca">
      <h2 id="titulo-busca">Buscar ocupação</h2>
      <form role="search" onSubmit={(evento) => { evento.preventDefault(); buscar(termo); }}>
        <label htmlFor="campo-busca">Nome da ocupação</label>
        <input
          id="campo-busca"
          type="search"
          value={termo}
          onChange={(evento) => setTermo(evento.target.value)}
          placeholder="Ex.: enfermagem, analista"
          autoComplete="off"
          maxLength={100}
        />
      </form>

      <p className="busca-aviso" role="status" aria-live="polite">{aviso}</p>
      {status === 'erro' && <p className="mensagem-erro" role="alert">{mensagem}</p>}

      {status === 'pronto' && resultados.length > 0 && (
        <ul className="lista-resultados">
          {resultados.map((ocupacao) => (
            <li key={ocupacao.id}>
              <button
                type="button"
                aria-pressed={ocupacao.id === selecionadoId}
                onClick={() => onSelecionar(ocupacao.id)}
              >
                <span className="resultado-nome">{ocupacao.nome}</span>
                {ocupacao.codigo_cbo && <span className="resultado-cbo">CBO {ocupacao.codigo_cbo}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
