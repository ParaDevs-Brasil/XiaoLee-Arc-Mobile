import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '@/api/client';

/**
 * Busca dado do backend com o ciclo que toda tela de lista precisa: primeira
 * carga, erro exibível e recarga manual.
 *
 * Generaliza o que `app/diagnostics.tsx` já fazia à mão. O cuidado que vale
 * preservar dali: `loading` nasce `true` e o resultado só é aplicado dentro do
 * `then`, nunca de forma síncrona no corpo do efeito — o React Compiler (ligado
 * em `app.json`) trata isso como render em cascata (`react-hooks/set-state-in-effect`).
 */

export interface BackendData<T> {
  data: T | null;
  /** Já exibível ao usuário — `ApiError` normaliza a mensagem. */
  error: string | null;
  /** Primeira carga: ainda não há nada na tela para mostrar. */
  loading: boolean;
  /** Recarga com dado já na tela — é o que alimenta o `RefreshControl`. */
  refreshing: boolean;
  reload: () => void;
}

export function useBackendData<T>(fetcher: () => Promise<T>): BackendData<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // As telas tendem a passar uma arrow inline. Se `fetcher` entrasse nas
  // dependências do efeito de carga, cada render dispararia uma requisição
  // nova; o ref guarda sempre a última versão sem participar das deps.
  const latest = useRef(fetcher);
  useEffect(() => {
    latest.current = fetcher;
  });

  // Uma resposta que chega depois da tela sair não deve virar setState — além
  // do aviso, sobrescreveria o estado de quem entrou no lugar.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const run = useCallback(async () => {
    try {
      const next = await latest.current();
      if (!mounted.current) return;
      setData(next);
      // Sucesso limpa o erro anterior: senão a tela mostraria dado novo com um
      // aviso velho de falha em cima.
      setError(null);
    } catch (err) {
      if (!mounted.current) return;
      setError(err instanceof ApiError ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    run().then(() => {
      if (mounted.current) setLoading(false);
    });
  }, [run]);

  const reload = useCallback(() => {
    setRefreshing(true);
    run().then(() => {
      if (mounted.current) setRefreshing(false);
    });
  }, [run]);

  return { data, error, loading, refreshing, reload };
}
