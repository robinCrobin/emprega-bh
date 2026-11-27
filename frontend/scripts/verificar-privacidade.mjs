/**
 * Auditoria de privacidade das respostas da API (A17, apoia o CT-UI-04).
 *
 * Percorre as ocupações da API (ids 1, 2, 3...) e confere se os JSONs de busca e de série têm
 * só os campos do contrato e nenhum texto com cara de CNPJ, CPF ou e-mail.
 * Mostra apenas caminhos de campos, nunca valores.
 *
 * Uso (na pasta frontend): npm run verificar:privacidade -- [URL_DA_API]
 * Padrão: http://127.0.0.1:8000
 */
import { sanitizarBusca, sanitizarSerie } from '../src/lib/privacidade.js';

const base = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const MAX_ID = 500;
const FALHAS_SEGUIDAS_PARA_PARAR = 5;

async function obterJson(caminho) {
  let resposta;
  try {
    resposta = await fetch(`${base}${caminho}`, { headers: { Accept: 'application/json' } });
  } catch {
    console.error(`Não foi possível acessar a API em ${base}. Ela está em execução?`);
    process.exit(1);
  }
  if (resposta.status === 404) return null;
  if (!resposta.ok) {
    console.error(`Resposta inesperada (HTTP ${resposta.status}) em ${caminho}.`);
    process.exit(1);
  }
  return resposta.json();
}

const problemas = [];
function conferir(origem, { descartados }) {
  for (const caminho of descartados) problemas.push(`${origem}: campo fora do contrato ou mascarado em "${caminho}"`);
}

let ocupacoes = 0;
let seguidas = 0;
for (let id = 1; id <= MAX_ID && seguidas < FALHAS_SEGUIDAS_PARA_PARAR; id += 1) {
  const serie = await obterJson(`/ocupacoes/${id}/serie`);
  if (serie === null) { seguidas += 1; continue; }
  seguidas = 0;
  ocupacoes += 1;
  conferir(`/ocupacoes/${id}/serie`, sanitizarSerie(serie));
  if (id === 1 || ocupacoes % 25 === 0) {
    const busca = await obterJson(`/ocupacoes?q=${encodeURIComponent(serie.ocupacao.nome.slice(0, 4))}`);
    if (busca) conferir(`/ocupacoes?q=…`, sanitizarBusca(busca));
  }
}

console.log(`Ocupações verificadas em ${base}: ${ocupacoes}`);
if (ocupacoes === 0) {
  console.error('Nenhuma ocupação encontrada: carregue o banco (seed ou carga) antes de auditar.');
  process.exit(1);
}
if (problemas.length > 0) {
  console.error(`REPROVADO: ${problemas.length} problema(s) de privacidade.`);
  [...new Set(problemas)].slice(0, 50).forEach((problema) => console.error(` - ${problema}`));
  process.exit(1);
}
console.log('APROVADO: só campos do contrato, sem CNPJ, CPF, e-mail ou identificador de vaga.');
