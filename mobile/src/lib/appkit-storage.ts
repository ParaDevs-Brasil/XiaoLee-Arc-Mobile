import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Implementação mínima da interface `Storage` que `createAppKit` exige, em
 * cima do `AsyncStorage` que o app já usa em todo o resto (`lib/session.ts`).
 * A lib não empacota uma pronta — só define o contrato.
 */
export const appKitStorage = {
  async getKeys(): Promise<string[]> {
    return [...(await AsyncStorage.getAllKeys())];
  },
  async getEntries<T = unknown>(): Promise<[string, T][]> {
    const keys = await AsyncStorage.getAllKeys();
    const pairs = await AsyncStorage.multiGet(keys);
    return pairs
      .filter((pair): pair is [string, string] => pair[1] !== null)
      .map(([key, value]) => [key, JSON.parse(value) as T]);
  },
  async getItem<T = unknown>(key: string): Promise<T | undefined> {
    const raw = await AsyncStorage.getItem(key);
    return raw === null ? undefined : (JSON.parse(raw) as T);
  },
  async setItem<T = unknown>(key: string, value: T): Promise<void> {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  },
  async removeItem(key: string): Promise<void> {
    await AsyncStorage.removeItem(key);
  },
};
