import assert from 'node:assert/strict';
import { test } from 'node:test';
import { escalaY, montarGrafico, passoDosRotulos } from '../src/lib/grafico.js';
import { formatarAlgoritmo, formatarVagas } from '../src/lib/formato.js';

const serie = [
  { periodo: '2025-T1', quantidade_vagas: 10 },
  { periodo: '2025-T2', quantidade_vagas: 30 },
  { periodo: '2025-T3', quantidade_vagas: 20 },
];

test('escalaY usa topo e marcações redondas a partir de zero', () => {
  const escala = escalaY(132);
  assert.equal(escala.topo, 150);
  assert.deepEqual(escala.valores, [0, 50, 100, 150]);
});

test('escalaY aceita séries zeradas e valores pequenos', () => {
  assert.deepEqual(escalaY(0).valores, [0, 1]);
  assert.ok(escalaY(3).valores.every(Number.isInteger));
});

test('montarGrafico mantém a ordem cronológica e o eixo vertical invertido', () => {
  const g = montarGrafico({ serie, largura: 400, altura: 300 });
  assert.deepEqual(g.historico.map((p) => p.periodo), ['2025-T1', '2025-T2', '2025-T3']);
  assert.ok(g.historico[0].x < g.historico[1].x && g.historico[1].x < g.historico[2].x);
  assert.ok(g.historico[1].y < g.historico[0].y, 'mais vagas fica mais acima (y menor)');
  assert.equal(g.estimativa, null);
  assert.equal(g.linhaEstimativa, null);
  assert.equal(g.marcacoesX.length, 3);
});

test('montarGrafico acrescenta o trimestre estimado depois do último histórico', () => {
  const previsao = { trimestre_alvo: '2025-T4', quantidade_estimada: 25 };
  const g = montarGrafico({ serie, previsao, largura: 400, altura: 300 });
  assert.equal(g.estimativa.periodo, '2025-T4');
  assert.ok(g.estimativa.x > g.historico.at(-1).x);
  assert.equal(g.estimativa.x, g.area.direita);
  assert.ok(g.linhaEstimativa.startsWith(`M${g.historico.at(-1).x.toFixed(1)}`));
  assert.equal(g.historico.length, serie.length, 'a estimativa não entra no histórico');
});

test('a escala comporta a estimativa quando ela supera o histórico', () => {
  const previsao = { trimestre_alvo: '2025-T4', quantidade_estimada: 500 };
  const g = montarGrafico({ serie, previsao, largura: 400, altura: 300 });
  assert.ok(g.escala.topo >= 500);
  assert.ok(g.estimativa.y >= g.area.topo);
});

test('passoDosRotulos evita sobreposição e inclui sempre o último ponto', () => {
  assert.equal(passoDosRotulos(5, 600), 1);
  assert.ok(passoDosRotulos(25, 280) > 1);
  const previsao = { trimestre_alvo: '2025-T4', quantidade_estimada: 25 };
  const g = montarGrafico({ serie, previsao, largura: 120, altura: 220 });
  assert.equal(g.marcacoesX.at(-1).periodo, '2025-T4');
});

test('formatação de vagas e algoritmos', () => {
  assert.equal(formatarVagas(78.5), '79');
  assert.equal(formatarVagas(1234), (1234).toLocaleString('pt-BR'));
  assert.equal(formatarAlgoritmo('regressao_linear'), 'Regressão linear');
  assert.equal(formatarAlgoritmo('outro_modelo'), 'outro modelo');
});
