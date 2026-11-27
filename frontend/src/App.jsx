import { useState } from 'react';
import { usandoMock } from './api.js';
import BuscaOcupacao from './components/BuscaOcupacao.jsx';
import PainelOcupacao from './components/PainelOcupacao.jsx';

export default function App() {
  const [ocupacaoId, setOcupacaoId] = useState(null);

  return (
    <div className="aplicacao">
      <header className="topo">
        <h1>EmpregaBH</h1>
        <p>Vagas ofertadas em Belo Horizonte por ocupação, por trimestre.</p>
        {usandoMock && (
          <p className="faixa-mock" role="note">
            Modo de desenvolvimento: dados fictícios, sem relação com os dados da PBH.
          </p>
        )}
      </header>
      <main className="conteudo">
        <BuscaOcupacao selecionadoId={ocupacaoId} onSelecionar={setOcupacaoId} />
        <PainelOcupacao ocupacaoId={ocupacaoId} />
      </main>
      <footer className="rodape">
        <p>
          Os números são totais de vagas agregados por ocupação e trimestre, a partir de dados
          públicos da PBH. Esta página não mostra nem guarda dados de empresas, de vagas
          individuais ou de pessoas.
        </p>
      </footer>
    </div>
  );
}
