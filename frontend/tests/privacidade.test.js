import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { MASCARA, contemDocumentoPessoal, sanitizarBusca, sanitizarSerie } from '../src/lib/privacidade.js';
import { buscarOcupacoesMock, obterSerieMock } from '../src/mock/api.js';
import { OCUPACOES } from '../src/mock/dados.js';

const sem = { atrasoMs: 0 };

test('campos fora do contrato (CNPJ, vaga, empresa) são descartados e só o caminho é informado', () => {
  const resposta = {
    termo: 'x', total_retornado: 1,
    resultados: [{ id: 1, nome: 'Analista', codigo_cbo: '999101', cnpj: '12.345.678/0001-95', empresa: 'ACME' }],
    id_vaga: 77,
  };
  const { dados, descartados } = sanitizarBusca(resposta);
  assert.deepEqual(dados.resultados[0], { id: 1, nome: 'Analista', codigo_cbo: '999101' });
  assert.equal('id_vaga' in dados, false);
  assert.deepEqual([...descartados].sort(), ['id_vaga', 'resultados[].cnpj', 'resultados[].empresa']);
  assert.ok(!JSON.stringify(descartados).includes('12.345'), 'nenhum valor é repetido');
});

test('campos extras aninhados na série também são removidos', async () => {
  const base = await obterSerieMock(1, sem);
  base.serie[0].cnpj_empresa = '12345678000195';
  base.previsao.detalhe = { pessoa: 'x' };
  base.ocupacao.id_vaga = 5;
  const { dados, descartados } = sanitizarSerie(base);
  assert.equal('cnpj_empresa' in dados.serie[0], false);
  assert.equal('detalhe' in dados.previsao, false);
  assert.equal('id_vaga' in dados.ocupacao, false);
  assert.equal(descartados.length, 3);
});

test('textos com CNPJ, CPF ou e-mail são mascarados mesmo em campos permitidos', async () => {
  const base = await obterSerieMock(1, sem);
  base.ocupacao.nome = 'Vaga da empresa 12.345.678/0001-95';
  base.motivo_sem_previsao = 'fale com ana@exemplo.com';
  const { dados, descartados } = sanitizarSerie(base);
  assert.equal(dados.ocupacao.nome, MASCARA);
  assert.equal(dados.motivo_sem_previsao, MASCARA);
  assert.deepEqual([...descartados].sort(), ['motivo_sem_previsao', 'ocupacao.nome']);
});

test('detecção de documentos não confunde CBO nem períodos', () => {
  assert.equal(contemDocumentoPessoal('999101'), false);
  assert.equal(contemDocumentoPessoal('2026-T4'), false);
  assert.equal(contemDocumentoPessoal('12345678000195'), true);
  assert.equal(contemDocumentoPessoal('123.456.789-09'), true);
});

test('respostas do mock já seguem o contrato: nada é descartado (CT-UI-04)', async () => {
  const busca = sanitizarBusca(await buscarOcupacoesMock('te', sem));
  assert.deepEqual(busca.descartados, []);
  for (const { id } of OCUPACOES) {
    const original = await obterSerieMock(id, sem);
    const { dados, descartados } = sanitizarSerie(original);
    assert.deepEqual(descartados, [], `ocupação ${id}`);
    assert.deepEqual(dados, original, `ocupação ${id} não pode perder campos do contrato`);
  }
});

function arquivosFonte(pasta) {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = join(pasta, nome);
    return statSync(caminho).isDirectory() ? arquivosFonte(caminho) : [caminho];
  });
}

test('o código da interface não grava dados no navegador nem usa rastreamento', () => {
  const pasta = fileURLToPath(new URL('../src', import.meta.url));
  const proibidos = /localStorage|sessionStorage|document\.cookie|indexedDB|sendBeacon|dangerouslySetInnerHTML|gtag\(|google-analytics/;
  for (const arquivo of arquivosFonte(pasta)) {
    if (!/\.(js|jsx)$/.test(arquivo)) continue;
    assert.doesNotMatch(readFileSync(arquivo, 'utf8'), proibidos, arquivo);
  }
});
