import auth, { type FirebaseAuthTypes } from '@react-native-firebase/auth';
import { GoogleSignin, statusCodes } from '@react-native-google-signin/google-signin';

/**
 * Login com Google → Firebase Auth.
 *
 * O fluxo é em duas etapas porque o Firebase não abre a tela de escolher
 * conta: o `google-signin` faz isso nativamente e devolve um idToken, que
 * então vira uma credencial do Firebase.
 *
 * O `webClientId` é o OAuth client **type 3 (web)** do google-services.json —
 * não o type 1 (android). Usar o android aqui faz o login falhar com
 * DEVELOPER_ERROR, que é o erro mais comum dessa integração.
 */
const WEB_CLIENT_ID =
  '347296354021-p6i6cf8c7i28cm8265q905jc9bpovvio.apps.googleusercontent.com';

let configured = false;

function ensureConfigured(): void {
  if (configured) return;
  GoogleSignin.configure({ webClientId: WEB_CLIENT_ID });
  configured = true;
}

/** Erro de fluxo esperado (usuário cancelou etc.) — não é bug, não logar como tal. */
export class GoogleSignInCancelled extends Error {
  constructor() {
    super('Login com Google cancelado.');
    this.name = 'GoogleSignInCancelled';
  }
}

/**
 * Abre o seletor de conta Google e autentica no Firebase.
 * Lança `GoogleSignInCancelled` se o usuário desistir.
 */
export async function signInWithGoogle(): Promise<FirebaseAuthTypes.UserCredential> {
  ensureConfigured();

  // Sem Play Services o SDK nativo não sobe a tela de conta (só Android).
  await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });

  let idToken: string | null;
  try {
    const response = await GoogleSignin.signIn();
    // v13+ devolve { type: 'success' | 'cancelled', data }
    if (response.type === 'cancelled') throw new GoogleSignInCancelled();
    idToken = response.data.idToken;
  } catch (err) {
    if (err instanceof GoogleSignInCancelled) throw err;
    if ((err as { code?: string }).code === statusCodes.SIGN_IN_CANCELLED) {
      throw new GoogleSignInCancelled();
    }
    throw err;
  }

  if (!idToken) throw new Error('Google não devolveu idToken.');

  const credential = auth.GoogleAuthProvider.credential(idToken);
  return auth().signInWithCredential(credential);
}

/** Encerra a sessão nos dois lados — só Firebase deixaria a conta Google grudada. */
export async function signOut(): Promise<void> {
  ensureConfigured();
  await Promise.all([GoogleSignin.signOut(), auth().signOut()]);
}

/** Usuário atual do Firebase, ou null. Síncrono — use `onAuthChanged` para reagir. */
export function currentUser(): FirebaseAuthTypes.User | null {
  return auth().currentUser;
}

/** Assina mudanças de sessão. Retorna a função de unsubscribe. */
export function onAuthChanged(
  cb: (user: FirebaseAuthTypes.User | null) => void,
): () => void {
  return auth().onAuthStateChanged(cb);
}

/**
 * ID token do Firebase para mandar ao backend, que deve **verificar a
 * assinatura** com o Admin SDK antes de emitir sessão.
 */
export async function getFirebaseIdToken(): Promise<string | null> {
  const user = auth().currentUser;
  return user ? user.getIdToken() : null;
}
