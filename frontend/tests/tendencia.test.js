import assert from 'node:assert/strict';
import { test } from 'node:test';
import { descreverTendencia, formatarVariacao } from '../src/lib/formato.js';
import { obterSerieMock } from '../src/mock/api.js';

const sem = { atrasoMs: 0 };
const tendenciaDe = async (id) => (await obterSerieMock(id, sem)).tendencia;

test('descreverTendencia usa texto e símbolo, não só cor', () => {
  assert.deepEqual(descreverTendencia('crescente'), { texto: 'Crescente', simbolo: '▲', classe: 'crescente' });
  assert.equal(descreverTendencia('decrescente').simbolo, '▼');
  assert.equal(descreverTendencia('estável').texto, 'Estável');
});

test('formatarVariacao mostra sinal e vírgula decimal', () => {
  assert.equal(formatarVariacao(22.4), '+22,4%');
  assert.equal(formatarVariacao(-8), '−8,0%');
  assert.equal(formatarVariacao(0), '0,0%');
});

test('mock cobre tendência crescente, estável e decrescente (CT-UI-02)', async () => {
  assert.equal((await tendenciaDe(1)).classificacao, 'crescente');
  assert.equal((await tendenciaDe(4)).classificacao, 'estável');
  assert.equal((await tendenciaDe(5)).classificacao, 'decrescente');
});

test('tendência indisponível traz o motivo e não traz percentual', async () => {
  for (const id of [2, 7]) { // 7 trimestres; base anterior zero
    const t = await tendenciaDe(id);
    assert.equal(t.disponivel, false, `ocupação ${id}`);
    assert.equal(t.variacao_percentual, null);
    assert.ok(t.motivo.length > 0);
  }
});

test('estimativa sempre acompanha o aviso e só existe com histórico suficiente', async () => {
  for (const id of [1, 2, 3, 4, 5, 6, 7]) {
    const r = await obterSerieMock(id, sem);
    assert.match(r.aviso, /estimativa/i);
    assert.match(r.aviso, /não é uma recomendação profissional/);
    if (r.previsao) {
      assert.equal(r.historico_suficiente, true);
      assert.ok(r.informacoes_usadas.length > 0);
    } else {
      assert.ok(r.motivo_sem_previsao.length > 0);
      assert.deepEqual(r.informacoes_usadas, []);
    }
  }
});
