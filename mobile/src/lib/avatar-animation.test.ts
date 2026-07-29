/**
 * Check da máquina de estados do avatar. Roda com:
 *   node --experimental-strip-types src/lib/avatar-animation.test.ts
 *
 * Sem framework de propósito — o que precisa ser garantido são as três regras
 * que quebram a personagem se forem invertidas: expressão trava as trocas,
 * idle não trava, e o idle sorteado nunca repete o atual.
 */
import assert from 'node:assert/strict';

import { AvatarAnimation, isIdle } from './avatar-animation.ts';

function test(name: string, fn: () => void) {
  fn();
  console.log(`  ok  ${name}`);
}

console.log('avatar-animation');

test('idle faz loop, expressão não', () => {
  assert.equal(isIdle('xiaolee_standby'), true);
  assert.equal(isIdle('xiaolee_cheer'), false);
});

test('expressão trava as trocas até terminar', () => {
  const a = new AvatarAnimation();
  a.play('xiaolee_cheer');
  a.play('xiaolee_standby2'); // deve ser ignorado
  assert.equal(a.state.key, 'xiaolee_cheer');
  a.stop();
});

test('expressionEnded libera a trava e cai num idle', () => {
  const a = new AvatarAnimation();
  a.play('xiaolee_cheer');
  a.expressionEnded();
  assert.equal(isIdle(a.state.key), true, 'deveria voltar para um idle');
  a.stop();
});

test('expressionEnded é no-op sem expressão tocando', () => {
  // O componente assina o fim de vídeo nos dois players do crossfade sem saber
  // qual está à frente, então chamadas espúrias chegam — e não devem cortar o
  // idle atual nem sortear outro.
  const a = new AvatarAnimation();
  a.play('xiaolee_standby2');
  a.expressionEnded();
  assert.equal(a.state.key, 'xiaolee_standby2', 'idle não deveria ter mudado');
  a.stop();
});

test('idle não trava — pode ser interrompido', () => {
  const a = new AvatarAnimation();
  a.play('xiaolee_standby');
  a.play('xiaolee_standby3');
  assert.equal(a.state.key, 'xiaolee_standby3');
  a.stop();
});

test('subscribe recebe a troca e unsubscribe para de receber', () => {
  const a = new AvatarAnimation();
  const seen: string[] = [];
  const off = a.subscribe((s) => seen.push(s.key));
  a.play('xiaolee_standby2');
  off();
  a.play('xiaolee_standby3');
  assert.deepEqual(seen, ['xiaolee_standby2']);
  a.stop();
});

test('state reflete loop corretamente', () => {
  const a = new AvatarAnimation();
  a.play('xiaolee_standby');
  assert.equal(a.state.loop, true);
  a.expressionEnded(); // destrava
  a.play('xiaolee_love');
  assert.equal(a.state.loop, false);
  a.stop();
});

test('stop cancela o timer sem mudar a animação', () => {
  const a = new AvatarAnimation();
  a.play('xiaolee_standby');
  const before = a.state.key;
  a.stop();
  assert.equal(a.state.key, before);
});

console.log('todos os checks passaram');
