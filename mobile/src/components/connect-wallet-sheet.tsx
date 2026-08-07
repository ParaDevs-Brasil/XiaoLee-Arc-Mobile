import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useEffect } from 'react';

import { IconClose, IconWallet } from '@/components/icons';
import { useWalletConnect } from '@/lib/walletconnect';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Modal nativo de conexão de carteira via WalletConnect.
 *
 * Abre o picker de wallets EVM do celular (Metamask, Rainbow, Trust Wallet,
 * etc.). Conectar já é a identidade do app (`lib/walletconnect.tsx` grava a
 * sessão local ao conectar) — não há mais um POST de vínculo para esperar.
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
  const { isConnected, address, openModal } = useWalletConnect();

  // Conectou: o sheet cumpriu o papel e sai da frente. Quem lê o endereço é o
  // `useWallet`, direto do provider — não há estado para devolver para cima.
  useEffect(() => {
    if (isConnected && address && visible) onClose();
  }, [isConnected, address, visible, onClose]);

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
              <Text style={styles.subtitle}>ARC · EVM · USDC</Text>
            </View>
            <Pressable onPress={onClose} hitSlop={Spacing.two} accessibilityLabel="Close">
              <IconClose size={18} color={Colors.light.ink3} />
            </Pressable>
          </View>

          {isConnected && address ? (
            <>
              <Text style={styles.hint}>
                Wallet connected. The address {short(address)} is linked to your account.
              </Text>
              <View style={styles.connectedBox}>
                <IconWallet size={16} color={Colors.light.success} />
                <Text style={styles.connectedAddress}>{short(address)}</Text>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.hint}>
                Connect your EVM wallet to receive USDC. Xiaolee uses WalletConnect — your
                private key never leaves the device.
              </Text>

              <Pressable
                onPress={openModal}
                style={({ pressed }) => [styles.button, pressed && styles.pressed]}
                accessibilityRole="button"
              >
                <Text style={styles.buttonLabel}>Connect WalletConnect</Text>
              </Pressable>
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
  button: {
    height: 46,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  buttonLabel: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.card },
  pressed: { opacity: 0.7 },
});
