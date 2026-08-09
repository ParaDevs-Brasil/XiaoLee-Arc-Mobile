import { useLoginWithEmail, useLoginWithOAuth } from '@privy-io/expo';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Path, Svg } from 'react-native-svg';

import { IconClose, IconWallet } from '@/components/icons';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { usePrivyWallet } from '@/lib/wallet';

/**
 * Sheet de "Connect Wallet" (Privy por baixo). Substitui o modal de conexão
 * de carteira externa — não há mais app de carteira envolvido, a carteira
 * embutida nasce junto com a conta assim que o login (email ou Google)
 * completa (`lib/wallet.tsx`). O texto continua "Connect Wallet" de
 * propósito: pro usuário é a mesma ação de sempre, só muda o que acontece por
 * trás.
 *
 * Bottom sheet (desliza de baixo, cantos só em cima) em vez de modal
 * centralizado — mesmo formato que o seletor de carteira do WalletConnect
 * tinha, que é o padrão que o usuário reconhece.
 */

interface ConnectWalletSheetProps {
  visible: boolean;
  onClose: () => void;
}

/** Abrevia o endereço como no perfil (0x1234…5678). */
function short(address: string): string {
  return address.length <= 16 ? address : `${address.slice(0, 6)}…${address.slice(-4)}`;
}

/**
 * Logo oficial do Google, 4 cores — as diretrizes de marca deles exigem o
 * mark colorido em botões "Sign in/Continue with Google", não uma versão
 * monocromática. Por isso fica fora de `components/icons.tsx`: aquele
 * arquivo é stroke-based e de uma cor só, de propósito (seção 4 do design
 * system) — este é o único ícone do app que quebra essa regra, e quebra por
 * exigência de marca de terceiro, não por escolha nossa.
 */
function GoogleLogo({ size = 18 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 18 18">
      <Path
        fill="#4285F4"
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"
      />
      <Path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
      />
      <Path
        fill="#FBBC05"
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
      />
      <Path
        fill="#EA4335"
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
      />
    </Svg>
  );
}

export function ConnectWalletSheet({ visible, onClose }: ConnectWalletSheetProps) {
  const insets = useSafeAreaInsets();
  const { isConnected, address } = usePrivyWallet();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const { state: emailState, sendCode, loginWithCode } = useLoginWithEmail();
  const { login: loginWithGoogle, state: oauthState } = useLoginWithOAuth();

  // Conectou: o sheet cumpriu o papel e sai da frente. Quem lê o endereço é o
  // `useWallet`, direto do provider — não há estado para devolver para cima.
  useEffect(() => {
    if (isConnected && address && visible) onClose();
  }, [isConnected, address, visible, onClose]);

  // Limpa o formulário quando o sheet fecha sem completar — reabrir não deve
  // reencontrar um código velho de uma tentativa anterior.
  //
  // `setState` não roda direto no corpo do efeito (o lint do React barra, e
  // com razão: dispararia render em cascata) — quem chama é o `.then()`, que
  // já roda fora do render, mesmo acordo do `lib/wallet.tsx`.
  useEffect(() => {
    if (visible) return;
    Promise.resolve().then(() => {
      setEmail('');
      setCode('');
    });
  }, [visible]);

  const awaitingCode = emailState.status === 'awaiting-code-input';
  const busy =
    emailState.status === 'sending-code' ||
    emailState.status === 'submitting-code' ||
    oauthState.status === 'loading';
  const failed = emailState.status === 'error' || oauthState.status === 'error';

  async function submitEmail() {
    if (!email.trim().includes('@') || busy) return;
    await sendCode({ email: email.trim() });
  }

  async function submitCode() {
    if (!code.trim() || busy) return;
    await loginWithCode({ code: code.trim(), email: email.trim() });
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      {/* `Modal` abre a própria janela nativa, por cima de tudo — o
          `KeyboardAvoidingView` do composer do chat não alcança aqui dentro,
          então o sheet precisa do seu próprio. Mesmo `behavior="padding"` nas
          duas plataformas, pelo mesmo motivo do composer: a raiz desta árvore
          já começa no topo da janela do Modal, e desde o edge-to-edge
          obrigatório (SDK 54) a janela não encolhe mais sozinha. */}
      <KeyboardAvoidingView style={styles.flexFill} behavior="padding">
        <Pressable style={styles.backdrop} onPress={onClose}>
          <Pressable
            style={[styles.sheet, { paddingBottom: Spacing.four + insets.bottom }]}
            onPress={(event) => event.stopPropagation()}
          >
            <View style={styles.handle} />

            <View style={styles.header}>
              <View style={styles.icon}>
                <IconWallet size={20} color={Colors.light.accent} />
              </View>
              <View style={styles.headerText}>
                <Text style={styles.title}>Connect Wallet</Text>
                <Text style={styles.subtitle}>ARC · EVM · USDC</Text>
              </View>
              <Pressable onPress={onClose} hitSlop={Spacing.two} accessibilityLabel="Close">
                <IconClose size={18} color={Colors.light.ink3} />
              </Pressable>
            </View>

            {isConnected && address ? (
              <>
                <Text style={styles.hint}>
                  Connected. The address {short(address)} is linked to your account.
                </Text>
                <View style={styles.connectedBox}>
                  <IconWallet size={16} color={Colors.light.success} />
                  <Text style={styles.connectedAddress}>{short(address)}</Text>
                </View>
              </>
            ) : (
              <>
                <Text style={styles.hint}>
                  Connect with email or Google. Xiaolee creates and secures your wallet on Arc for
                  you — no seed phrase, no separate app.
                </Text>

                {!awaitingCode ? (
                  <TextInput
                    value={email}
                    onChangeText={setEmail}
                    placeholder="you@example.com"
                    placeholderTextColor={Colors.light.ink3}
                    keyboardType="email-address"
                    autoCapitalize="none"
                    autoComplete="email"
                    editable={!busy}
                    style={styles.input}
                  />
                ) : (
                  <>
                    <Text style={styles.codeHint}>Code sent to {email}</Text>
                    <TextInput
                      value={code}
                      onChangeText={setCode}
                      placeholder="123456"
                      placeholderTextColor={Colors.light.ink3}
                      keyboardType="number-pad"
                      editable={!busy}
                      style={styles.input}
                    />
                  </>
                )}

                {failed ? (
                  <Text style={styles.error}>Something went wrong. Try again.</Text>
                ) : null}

                <Pressable
                  onPress={awaitingCode ? submitCode : submitEmail}
                  disabled={busy}
                  style={({ pressed }) => [styles.button, (pressed || busy) && styles.pressed]}
                  accessibilityRole="button"
                >
                  {busy ? (
                    <ActivityIndicator color={Colors.light.card} />
                  ) : (
                    <Text style={styles.buttonLabel}>
                      {awaitingCode ? 'Verify code' : 'Continue with email'}
                    </Text>
                  )}
                </Pressable>

                {!awaitingCode ? (
                  <>
                    <View style={styles.divider}>
                      <View style={styles.dividerLine} />
                      <Text style={styles.dividerLabel}>or</Text>
                      <View style={styles.dividerLine} />
                    </View>

                    <Pressable
                      onPress={() => loginWithGoogle({ provider: 'google' })}
                      disabled={busy}
                      style={({ pressed }) => [
                        styles.googleButton,
                        (pressed || busy) && styles.pressed,
                      ]}
                      accessibilityRole="button"
                    >
                      <GoogleLogo size={18} />
                      <Text style={styles.googleButtonLabel}>Continue with Google</Text>
                    </Pressable>
                  </>
                ) : null}
              </>
            )}
          </Pressable>
        </Pressable>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  flexFill: { flex: 1 },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26,25,23,0.35)',
    justifyContent: 'flex-end',
  },
  sheet: {
    gap: Spacing.three - 4,
    paddingHorizontal: Spacing.four,
    paddingTop: Spacing.two,
    borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    ...CardShadow,
  },
  handle: {
    alignSelf: 'center',
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.light.border,
    marginBottom: Spacing.one,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two + 2 },
  icon: {
    width: 40,
    height: 40,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
  },
  headerText: { flex: 1 },
  title: { fontFamily: Fonts.bold, fontSize: 16, color: Colors.light.ink },
  subtitle: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 1 },
  hint: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 19, color: Colors.light.ink2 },
  codeHint: { fontFamily: Fonts.semibold, fontSize: 12, color: Colors.light.ink2 },
  connectedBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    padding: Spacing.three - 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.successSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.successBorder,
  },
  connectedAddress: {
    fontFamily: Fonts.mono,
    fontSize: 14,
    color: Colors.light.success,
  },
  input: {
    height: 46,
    paddingHorizontal: Spacing.three - 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    fontFamily: Fonts.medium,
    fontSize: 14,
    color: Colors.light.ink,
  },
  error: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.danger },
  button: {
    height: 46,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  buttonLabel: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.card },
  divider: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  dividerLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: Colors.light.border },
  dividerLabel: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink3 },
  googleButton: {
    height: 46,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two - 2,
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    backgroundColor: Colors.light.card,
  },
  googleButtonLabel: { fontFamily: Fonts.semibold, fontSize: 14, color: Colors.light.ink },
  pressed: { opacity: 0.7 },
});
