import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * Já viu a intro em vídeo alguma vez? A intro toca em toda abertura do app,
 * mas só a primeira vez é sem botão de pular — depois disso o usuário pode
 * saltar direto pro chat.
 *
 * Mesmo acordo do `lib/session.ts`: SecureStore no nativo, localStorage no
 * web (o SecureStore não existe em `expo start --web`).
 */
const SEEN_INTRO_KEY = 'xiaolee_seen_intro';

const isWeb = Platform.OS === 'web';

export async function hasSeenIntro(): Promise<boolean> {
  if (isWeb) {
    try {
      return globalThis.localStorage?.getItem(SEEN_INTRO_KEY) === '1';
    } catch {
      return false;
    }
  }
  return (await SecureStore.getItemAsync(SEEN_INTRO_KEY)) === '1';
}

export async function markIntroSeen(): Promise<void> {
  if (isWeb) {
    try {
      globalThis.localStorage?.setItem(SEEN_INTRO_KEY, '1');
    } catch {
      // storage indisponível (modo privado) — a próxima abertura pede de novo
    }
    return;
  }
  await SecureStore.setItemAsync(SEEN_INTRO_KEY, '1');
}
