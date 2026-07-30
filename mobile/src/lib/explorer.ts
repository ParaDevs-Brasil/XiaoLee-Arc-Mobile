/**
 * Links para o explorer de blocos da Arc.
 *
 * O feed de traction mostra o hash da transação, mas hash truncado não é prova
 * de nada para quem está olhando a tela — é prova quando dá para abrir. Daí
 * este módulo existir: a linha do feed vira um link verificável.
 */

/**
 * Copiado de `backend/server/routes/arc_routes.py` (`blockExplorerUrls`), que
 * hoje só devolve a testnet — o sprint inteiro roda com `ARC_SANDBOX=true`.
 *
 * Atenção: quando existir ambiente de mainnet, isto **não** pode continuar
 * sendo constante de bundle. O app apontaria para a testnet enquanto o backend
 * liquida na mainnet, e cada link do feed cairia num "transação não
 * encontrada". A URL precisa passar a vir do backend junto do resto da config
 * de chain.
 */
const ARC_EXPLORER_URL = 'https://testnet.arcscan.app';

/**
 * Nem todo pagamento do feed tem transação na chain: com a chain fora do ar o
 * agente enfileira e responde `"status": "queued"`, e sem chave de admin ele
 * roda em `dry_run`. Nesses casos o campo `tx` carrega um marcador, não um
 * hash — o backend repassa o valor como veio, sem normalizar.
 *
 * Por isso o teste é positivo (parece um hash de transação EVM) e não negativo
 * (não é um marcador conhecido): assim um marcador novo do backend deixa de
 * ser link em vez de virar um link quebrado.
 */
export function isOnChainTx(tx: string): boolean {
  return /^0x[0-9a-fA-F]{64}$/.test(tx);
}

export function txExplorerUrl(tx: string): string {
  return `${ARC_EXPLORER_URL}/tx/${tx}`;
}
