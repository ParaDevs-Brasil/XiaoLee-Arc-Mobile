import { useState } from 'react';
import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { IconClose, IconWallet } from '@/components/icons';
import { linkWallet } from '@/api/backend';
import { ApiError } from '@/api/client';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { saveWallet } from '@/lib/session';

/**
 * Vínculo do endereço de payout.
 *
 * A carteira é do usuário: a chave privada nunca chega ao servidor, só o
 * endereço. É o mesmo modelo do web (lá o Web3Auth deriva a chave no browser e
 * manda só o endereço), sem arrastar um SDK de carteira para o app.
 *
 * O backend valida o formato e confere o dono pela sessão — colar o endereço
 * de outra pessoa só faria você pagar a ela.
 */

interface ConnectWalletSheetProps {
  visible: boolean;
  onClose: () => void;
  onConnected: (address: string) => void;
}

export function ConnectWalletSheet({ visible, onClose, onConnected }: ConnectWalletSheetProps) {
  const [address, setAddress] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function connect() {
    const value = address.trim();
    if (!value || saving) return;

    setSaving(true);
    setError(null);
    try {
      const linked = await linkWallet(value);
      await saveWallet({ address: linked.address, chain: linked.chain });
      onConnected(linked.address);
      setAddress('');
      onClose();
    } catch (err) {
      // 401 aqui quase sempre significa "ainda não entrou", não token inválido.
      const status = err instanceof ApiError ? err.status : null;
      setError(
        status === 401
          ? 'Entre com o Google antes de conectar a carteira.'
          : err instanceof ApiError
            ? err.message
            : String(err),
      );
    } finally {
      setSaving(false);
    }
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
              <Text style={styles.title}>Connect Wallet</Text>
              <Text style={styles.subtitle}>ARC · Solana · Stellar · USDC</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={Spacing.two} accessibilityLabel="Fechar">
              <IconClose size={18} color={Colors.light.ink3} />
            </Pressable>
          </View>

          <Text style={styles.hint}>
            Cole o endereço da sua carteira EVM. É para onde a Xiaolee vai mandar seus USDC — a
            chave privada nunca sai do seu aparelho.
          </Text>

          <TextInput
            value={address}
            onChangeText={(next) => {
              setAddress(next);
              setError(null);
            }}
            placeholder="0x…"
            placeholderTextColor={Colors.light.ink3}
            style={[styles.input, error ? styles.inputError : null]}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!saving}
            onSubmitEditing={connect}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable
            onPress={connect}
            disabled={saving || address.trim().length === 0}
            style={({ pressed }) => [
              styles.button,
              (saving || address.trim().length === 0) && styles.buttonIdle,
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
          >
            {saving ? (
              <ActivityIndicator size="small" color={Colors.light.card} />
            ) : (
              <Text style={styles.buttonLabel}>Conectar</Text>
            )}
          </Pressable>
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
  input: {
    height: 48,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    backgroundColor: Colors.light.bg,
    fontFamily: Fonts.mono,
    fontSize: 13,
    color: Colors.light.ink,
  },
  inputError: { borderColor: Colors.light.danger },
  error: { fontFamily: Fonts.medium, fontSize: 12, color: Colors.light.danger },
  button: {
    height: 46,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  buttonIdle: { opacity: 0.45 },
  buttonLabel: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.card },
  pressed: { opacity: 0.7 },
});
