import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

/** Nunca há mudança a assinar: hidratou uma vez, hidratou para sempre. */
const subscribe = () => () => {};

/**
 * To support static rendering, this value needs to be re-calculated on the client side for web
 *
 * A detecção de hidratação é feita com `useSyncExternalStore` (snapshot do
 * servidor `false`, do cliente `true`) em vez de `setState` num efeito: com o
 * React Compiler ligado (`experiments.reactCompiler` no app.json), setState
 * síncrono dentro de efeito é erro de lint por causar render em cascata.
 */
export function useColorScheme() {
  const hasHydrated = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  const colorScheme = useRNColorScheme();

  if (hasHydrated) {
    return colorScheme;
  }

  return 'light';
}
