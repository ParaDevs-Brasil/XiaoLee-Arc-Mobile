/**
 * Check do parser de SSE. Roda com:
 *   node --experimental-strip-types src/lib/sse.test.ts
 *
 * Sem framework, como os outros checks do `lib/`. O caso que motiva o arquivo
 * é o pedaço partido: a rede corta no meio de uma linha, e tratar bloco
 * incompleto como evento entrega JSON truncado para o `JSON.parse` da tela.
 */
import assert from 'node:assert/strict';

import { parseSseChunk } from './sse.ts';

function test(name: string, fn: () => void) {
  fn();
  console.log(`  ok  ${name}`);
}

console.log('sse');

test('lê um evento nomeado', () => {
  const { events, rest } = parseSseChunk('event: payment_settled\ndata: {"amount":5}\n\n');
  assert.deepEqual(events, [{ event: 'payment_settled', data: '{"amount":5}' }]);
  assert.equal(rest, '');
});

test('lê vários eventos no mesmo pedaço', () => {
  const { events } = parseSseChunk('event: a\ndata: 1\n\nevent: b\ndata: 2\n\n');
  assert.deepEqual(events.map((e) => e.event), ['a', 'b']);
  assert.deepEqual(events.map((e) => e.data), ['1', '2']);
});

test('segura bloco incompleto no resto em vez de emitir truncado', () => {
  const { events, rest } = parseSseChunk('event: payment_settled\ndata: {"amo');
  assert.deepEqual(events, []);
  assert.equal(rest, 'event: payment_settled\ndata: {"amo');
});

test('junta o resto com o pedaço seguinte', () => {
  const first = parseSseChunk('event: payment_settled\ndata: {"amo');
  const second = parseSseChunk(first.rest + 'unt":5}\n\n');
  assert.deepEqual(second.events, [{ event: 'payment_settled', data: '{"amount":5}' }]);
  assert.equal(second.rest, '');
});

test('ignora o keepalive que o backend manda a cada 25s', () => {
  const { events, rest } = parseSseChunk(': keepalive\n\n');
  assert.deepEqual(events, []);
  assert.equal(rest, '');
});

test('keepalive entre dois eventos não engole nenhum', () => {
  const { events } = parseSseChunk('event: a\ndata: 1\n\n: keepalive\n\nevent: b\ndata: 2\n\n');
  assert.deepEqual(events.map((e) => e.event), ['a', 'b']);
});

test('evento sem nome vira message, como manda a espec', () => {
  const { events } = parseSseChunk('data: solto\n\n');
  assert.deepEqual(events, [{ event: 'message', data: 'solto' }]);
});

test('descarta um espaço depois dos dois-pontos, e só um', () => {
  const { events } = parseSseChunk('data:  dois espaços\n\n');
  assert.equal(events[0].data, ' dois espaços');
});

test('junta linhas data: do mesmo bloco com quebra', () => {
  const { events } = parseSseChunk('data: linha1\ndata: linha2\n\n');
  assert.equal(events[0].data, 'linha1\nlinha2');
});

test('aceita CRLF sem deixar o \\r no valor', () => {
  const { events } = parseSseChunk('event: a\r\ndata: 1\r\n\r\n');
  assert.deepEqual(events, [{ event: 'a', data: '1' }]);
});

test('bloco sem data não vira evento', () => {
  const { events } = parseSseChunk('event: vazio\n\n');
  assert.deepEqual(events, []);
});

console.log('todos os checks passaram');
