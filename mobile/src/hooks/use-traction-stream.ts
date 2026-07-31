import { useEffect, useState } from 'react';

import type { PaymentEvent, TractionSnapshot } from '@/api/backend';
import { API_URL } from '@/lib/config';
import { parseSseChunk } from '@/lib/sse';

/**
 * Liga a Traction ao stream `GET /v1/traction/feed`.
 *
 * O backend já emitia esses eventos e o docstring dele diz que o dashboard
 * deveria conectar "sem polling" — só ninguém tinha conectado. Com isto, uma
 * liquidação nova aparece na tela no instante em que o agente paga, em vez de
 * esperar o usuário puxar para atualizar.
 *
 * Usa `XMLHttpRequest` porque o React Native não tem `EventSource` e o `fetch`
 * dele não entrega corpo em pedaços: o XHR é a única API do runtime que expõe
 * resposta parcial, via `onprogress`.
 *
 * O que o stream manda:
 *   - `snapshot`        — o estado inteiro, na conexão
 *   - `payment_settled` — um pagamento
 *   - `: keepalive`     — a cada 25s, ignorado pelo parser
 */

/** Mesmo teto do backend (`metrics.py::_MAX_FEED`), para o feed não crescer sem fim. */
const MAX_FEED = 50;

/** Espera antes de reconectar. O stream cai em troca de rede, e cair é normal. */
const RECONNECT_MS = 4000;

export interface TractionStream {
  /** `null` enquanto não houver stream — a tela cai no dado do polling. */
  live: TractionSnapshot | null;
  connected: boolean;
}

export function useTractionStream(): TractionStream {
  const [live, setLive] = useState<TractionSnapshot | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let xhr: XMLHttpRequest | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (cancelled) return;

      // `responseText` acumula o stream inteiro, então guardamos até onde já
      // lemos em vez de reprocessar tudo a cada `onprogress`.
      let consumed = 0;
      let buffer = '';

      const request = new XMLHttpRequest();
      xhr = request;

      request.open('GET', `${API_URL}/v1/traction/feed`);
      request.setRequestHeader('Accept', 'text/event-stream');

      request.onprogress = () => {
        if (cancelled) return;
        setConnected(true);

        buffer += request.responseText.slice(consumed);
        consumed = request.responseText.length;

        const { events, rest } = parseSseChunk(buffer);
        buffer = rest;

        for (const event of events) {
          let payload: unknown;
          try {
            payload = JSON.parse(event.data);
          } catch {
            // Evento malformado não derruba o stream: o próximo vem inteiro.
            continue;
          }

          if (event.event === 'snapshot') {
            setLive(payload as TractionSnapshot);
          } else if (event.event === 'payment_settled') {
            setLive((current) => applyPayment(current, payload as PaymentEvent));
          }
        }
      };

      const scheduleReconnect = () => {
        if (cancelled) return;
        setConnected(false);
        retry = setTimeout(connect, RECONNECT_MS);
      };

      // `onload` também reconecta: um stream que termina sozinho é conexão
      // encerrada pelo servidor, não sucesso.
      request.onload = scheduleReconnect;
      request.onerror = scheduleReconnect;
      request.ontimeout = scheduleReconnect;

      request.send();
    }

    connect();

    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
      // `abort` dispara `onerror` em algumas implementações — o `cancelled`
      // acima é o que impede a reconexão depois de a tela sair.
      xhr?.abort();
    };
  }, []);

  return { live, connected };
}

/**
 * Aplica um pagamento ao snapshot em memória.
 *
 * Só mexe no que dá para derivar **exatamente** do evento: o valor entra no
 * total, a contagem sobe um, e o pagamento encabeça o feed.
 *
 * `active_creators` e as latências ficam paradas de propósito. Saber se este
 * creator já contava exigiria o conjunto inteiro, que o evento não traz, e o
 * feed vem cortado em 50 — então não dá para descobrir olhando. Somar um ali
 * seria inventar. Esses três voltam ao valor certo no próximo snapshot ou num
 * puxão para atualizar.
 */
function applyPayment(
  current: TractionSnapshot | null,
  event: PaymentEvent,
): TractionSnapshot | null {
  if (!current) return current;

  // O backend é idempotente por `intent_id`; o cliente precisa ser também,
  // senão uma reconexão que reenvie um evento contaria o pagamento duas vezes.
  if (current.feed.some((item) => item.intent_id === event.intent_id)) return current;

  return {
    ...current,
    total_usdc: current.total_usdc + event.amount,
    total_payments: current.total_payments + 1,
    feed: [event, ...current.feed].slice(0, MAX_FEED),
  };
}
