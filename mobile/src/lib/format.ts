/**
 * Formatação de valores vindos do backend.
 *
 * Vive aqui, e não na tela, por dois motivos: Campaigns, Dashboard e
 * Notifications formatam os mesmos tipos de dado, e assim as regras ficam
 * testáveis por `node --experimental-strip-types` — um arquivo de tela
 * arrastaria JSX e o runtime do React Native para dentro do teste.
 */

/**
 * O feed de traction serializa o instante com
 * `datetime.utcnow().isoformat() + "Z"`, que emite **microssegundos**
 * (ex.: `2026-07-30T19:26:09.001709Z`). O formato de data do ECMA-262 prevê
 * milissegundos — três casas —, e engines divergem no quanto toleram a mais;
 * um parse recusado viraria `NaN` e a tela mostraria "NaNs ago" no aparelho.
 * Cortar para três casas é aceito por todas.
 */
export function parseTimestamp(iso: string): number {
  return Date.parse(iso.replace(/(\.\d{3})\d+/, '$1'));
}

/**
 * Distância até agora, na mesma escala do web (`app/traction/page.tsx`):
 * segundos, minutos, horas. Devolve string vazia se a data não parsear —
 * é melhor não mostrar hora nenhuma do que mostrar lixo.
 */
export function timeAgo(iso: string, now: number = Date.now()): string {
  const at = parseTimestamp(iso);
  if (Number.isNaN(at)) return '';

  // `Math.max` protege contra relógio do aparelho atrasado em relação ao
  // servidor, que renderizaria "-3s ago".
  const seconds = Math.max(0, Math.floor((now - at) / 1000));
  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}min ago`;

  return `${Math.floor(minutes / 60)}h ago`;
}

/** Duas casas sempre — valores de USDC não devem dançar de largura na lista. */
export function formatUSDC(value: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Hash no formato do explorer: começo…fim. Abaixo do limite devolve inteiro,
 * senão encurtar deixaria o texto maior do que o original.
 */
export function shortHash(value: string): string {
  return value.length > 16 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value;
}
