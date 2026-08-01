/**
 * Parser de Server-Sent Events.
 *
 * Vive aqui, separado da conexão, por dois motivos: é lógica pura e o `lib/`
 * do projeto é testado com `node --experimental-strip-types`, sem arrastar o
 * runtime do React Native para dentro do teste.
 *
 * Escrito à mão em vez de trazer `react-native-sse` porque o React Native não
 * expõe `EventSource` e a alternativa era mais uma dependência — e o
 * `package.json` deste repo documenta duas quebras de CI causadas justamente
 * por drift de dependência. O protocolo cabe em trinta linhas.
 */

export interface SseEvent {
  /** `message` quando o servidor não nomeia o evento, como manda a espec. */
  event: string;
  data: string;
}

/**
 * Consome o que chegou até agora e devolve os eventos **completos** mais o
 * resto que ainda não fechou.
 *
 * O resto importa: pedaço de rede corta no meio de uma linha o tempo todo, e
 * tratar um bloco incompleto como evento produziria JSON truncado. Quem chama
 * guarda o `rest` e concatena no próximo pedaço.
 */
export function parseSseChunk(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  // Normaliza CRLF antes de procurar o separador: com `\r\n` o fim de evento é
  // `\r\n\r\n`, que uma busca por `\n\n` nunca encontra — o stream ficaria
  // acumulando para sempre sem emitir nada. Fazer isso na entrada também
  // resolve o `\r` que cai no fim de um pedaço e o `\n` que abre o seguinte:
  // o resto volta para cá concatenado e é normalizado na próxima passada.
  let rest = buffer.replace(/\r\n/g, '\n');

  // Um evento termina em linha em branco.
  let index = rest.indexOf('\n\n');
  while (index !== -1) {
    const parsed = parseBlock(rest.slice(0, index));
    if (parsed) events.push(parsed);

    rest = rest.slice(index + 2);
    index = rest.indexOf('\n\n');
  }

  return { events, rest };
}

function parseBlock(block: string): SseEvent | null {
  let event = 'message';
  const data: string[] = [];

  for (const raw of block.split('\n')) {
    // Servidor pode usar CRLF; o `\r` sobra no fim da linha depois do split.
    const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw;

    // Linha começando em dois-pontos é comentário. O backend manda
    // `: keepalive` a cada 25s só para a conexão não morrer — não é evento.
    if (line === '' || line.startsWith(':')) continue;

    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? '' : line.slice(colon + 1);
    // A espec manda descartar **um** espaço depois dos dois-pontos, e só um.
    if (value.startsWith(' ')) value = value.slice(1);

    if (field === 'event') event = value;
    else if (field === 'data') data.push(value);
  }

  // Bloco sem `data` não é evento — é keepalive ou campo que não usamos.
  if (data.length === 0) return null;

  // Múltiplas linhas `data:` no mesmo bloco se juntam com quebra de linha.
  return { event, data: data.join('\n') };
}
