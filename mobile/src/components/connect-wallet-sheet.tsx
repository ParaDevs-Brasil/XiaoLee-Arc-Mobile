import { useLoginWithEmail, useLoginWithOAuth } from '@privy-io/expo';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { IconClose, IconWallet } from '@/components/icons';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { usePrivyWallet } from '@/lib/wallet';

/**
 * Sheet de login social (Privy). Substitui o modal de conexão de carteira
 * externa — não há mais app de carteira envolvido, a carteira embutida nasce
 * junto com a conta assim que o login (email ou Google) completa
 * (`lib/wallet.tsx`, `PRIVY_EMBEDDED_WALLET_CONFIG`).
 */

interface ConnectWalletSheetProps {
  visible: boolean;
  onClose: () => void;
}

/** Abrevia o endereço como no perfil (0x1234…5678). */
function short(address: string): string {
  return address.length <= 16 ? address : `${address.slice(0, 6)}…${address.slice(-4)}`;
}

export function ConnectWalletSheet({ visible, onClose }: ConnectWalletSheetProps) {
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
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(event) => event.stopPropagation()}>
          <View style={styles.header}>
            <View style={styles.icon}>
              <IconWallet size={20} color={Colors.light.accent} />
            </View>
            <View style={styles.headerText}>
              <Text style={styles.title}>Sign in</Text>
              <Text style={styles.subtitle}>ARC · EVM · USDC</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={Spacing.two} accessibilityLabel="Close">
              <IconClose size={18} color={Colors.light.ink3} />
            </Pressable>
          </View>

          {isConnected && address ? (
            <>
              <Text style={styles.hint}>
                Signed in. The address {short(address)} is linked to your account.
              </Text>
              <View style={styles.connectedBox}>
                <IconWallet size={16} color={Colors.light.success} />
                <Text style={styles.connectedAddress}>{short(address)}</Text>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.hint}>
                Sign in with email or Google. Xiaolee creates and secures your wallet on Arc for
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

              {failed ? <Text style={styles.error}>Something went wrong. Try again.</Text> : null}

              <Pressable
                onPress={awaitingCode ? submitCode : submitEmail}
                disabled={busy}
                style={({ pressed }) => [
                  styles.button,
                  (pressed || busy) && styles.pressed,
                ]}
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
                    <Text style={styles.googleButtonLabel}>Continue with Google</Text>
                  </Pressable>
                </>
              ) : null}
            </>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26,25,23,0.35)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.four,
  },
  sheet: {
    width: '100%',
    maxWidth: 420,
    padding: Spacing.four,
    gap: Spacing.three - 4,
    borderRadius: Radius.xl,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    ...CardShadow,
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
