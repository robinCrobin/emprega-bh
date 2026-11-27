import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ErroApi } from '../src/erroApi.js';
import { MINIMO_TRIMESTRES, buscarOcupacoesMock, obterSerieMock } from '../src/mock/api.js';

const sem = { atrasoMs: 0 };
const ids = async (q) => (await buscarOcupacoesMock(q, sem)).resultados.map((o) => o.id);

test('busca ignora acento e caixa e devolve os mesmos ids', async () => {
  const esperado = await ids('tecnico');
  assert.ok(esperado.length >= 2);
  assert.deepEqual(await ids('TÉCNICO'), esperado);
  assert.deepEqual(await ids('Técnico'), esperado);
});

test('busca parcial exige todas as palavras no nome', async () => {
  assert.deepEqual(await ids('enferm'), [3]);
  assert.deepEqual(await ids('tecnico enfermagem'), [3]);
  assert.deepEqual(await ids('enfermagem tecnico'), [3]);
});

test('busca sem resultado devolve lista vazia', async () => {
  const resposta = await buscarOcupacoesMock('astronauta', sem);
  assert.equal(resposta.total_retornado, 0);
  assert.deepEqual(resposta.resultados, []);
});

test('termo inválido gera erro 422 e não expõe campos extras', async () => {
  await assert.rejects(buscarOcupacoesMock('a', sem), (e) => e instanceof ErroApi && e.status === 422);
  const [resultado] = (await buscarOcupacoesMock('analista', sem)).resultados;
  assert.deepEqual(Object.keys(resultado).sort(), ['codigo_cbo', 'id', 'nome']);
});

test('série com histórico suficiente traz previsão no trimestre seguinte', async () => {
  const resposta = await obterSerieMock(1, sem);
  assert.equal(resposta.total_trimestres, 24);
  assert.equal(resposta.serie.at(0).periodo, '2021-T1');
  assert.equal(resposta.serie.at(-1).periodo, '2026-T4');
  assert.equal(resposta.previsao.trimestre_alvo, '2027-T1');
  assert.equal(resposta.motivo_sem_previsao, null);
});

test('fronteira do mínimo: 8 trimestres geram previsão, 7 não', async () => {
  const oito = await obterSerieMock(3, sem);
  assert.equal(oito.total_trimestres, MINIMO_TRIMESTRES);
  assert.equal(oito.historico_suficiente, true);
  assert.ok(oito.previsao);

  const sete = await obterSerieMock(2, sem);
  assert.equal(sete.total_trimestres, 7);
  assert.equal(sete.historico_suficiente, false);
  assert.equal(sete.previsao, null);
  assert.match(sete.motivo_sem_previsao, /mínimo/);
  assert.equal(sete.serie.length, 7, 'histórico disponível é preservado');
});

test('histórico suficiente sem previsão gravada explica o motivo', async () => {
  const resposta = await obterSerieMock(4, sem);
  assert.equal(resposta.historico_suficiente, true);
  assert.equal(resposta.previsao, null);
  assert.match(resposta.motivo_sem_previsao, /ainda não foi gerada/);
});

test('série vem em ordem cronológica e ocupação inexistente dá 404', async () => {
  for (const id of [1, 2, 3, 4, 5, 6]) {
    const { serie } = await obterSerieMock(id, sem);
    const ordem = serie.map((p) => p.ano * 10 + p.trimestre);
    assert.deepEqual(ordem, [...ordem].sort((a, b) => a - b));
  }
  await assert.rejects(obterSerieMock(999, sem), (e) => e instanceof ErroApi && e.status === 404);
});

test('requisição cancelada é rejeitada com AbortError', async () => {
  const controlador = new AbortController();
  const pedido = obterSerieMock(1, { atrasoMs: 1000, signal: controlador.signal });
  controlador.abort();
  await assert.rejects(pedido, (e) => e.name === 'AbortError');
});
