import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { DropdownPanel, PanelRow, type PanelItem } from '@/components/dropdown-panel';
import {
  IconClipboard,
  IconClock,
  IconDownload,
  IconUpload,
  IconUser,
  IconWallet,
} from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Painel de perfil — frame "Xiaolee - Profile" (grupo `menu-profile`, 191x522).
 *
 * Cabeçalho com identidade, seis ações e o CTA de login no rodapé. O login
 * dispara o fluxo Google → Firebase → sessão do backend (`src/lib/auth.ts`),
 * que só roda no dev client: o Expo Go não carrega os módulos nativos do
 * Firebase.
 */

interface ProfileMenuProps {
  visible: boolean;
  onDismiss: () => void;
  /** Handle do usuário, quando há sessão. */
  handle?: string;
  /** Endereço de payout vinculado, quando há. */
  walletAddress?: string;
  onSignIn?: () => void;
  onConnectWallet?: () => void;
  signingIn?: boolean;
}

/** Abrevia o endereço como no web: início e fim, meio elidido. */
function short(address: string): string {
  return address.length <= 16 ? address : `${address.slice(0, 8)}…${address.slice(-6)}`;
}

export function ProfileMenu({
  visible,
  onDismiss,
  handle,
  walletAddress,
  onSignIn,
  onConnectWallet,
  signingIn,
}: ProfileMenuProps) {
  const connected = Boolean(walletAddress);

  // Só o Connect Wallet está ligado; as demais ainda não têm destino, então
  // seguem sem `onPress` em vez de abrir tela vazia.
  const actions: PanelItem[] = [
    { key: 'wallet', Icon: IconWallet, title: 'wallet', subtitle: 'View token balance' },
    { key: 'transaction', Icon: IconClipboard, title: 'Transaction', subtitle: 'View swap history' },
    {
      key: 'history',
      Icon: IconClock,
      title: 'History',
      subtitle: 'View conversations and activities',
    },
    {
      key: 'connect',
      Icon: IconClipboard,
      title: connected ? 'Wallet conectada' : 'Connect Wallet',
      subtitle: walletAddress ? short(walletAddress) : 'ARC - Solana - Stellar - USDC',
      onPress: () => {
        onDismiss();
        onConnectWallet?.();
      },
    },
    { key: 'withdraw', Icon: IconDownload, title: 'Withdraw', subtitle: 'Withdraw funds to wallet' },
    { key: 'deposit', Icon: IconUpload, title: 'Deposit', subtitle: 'Add funds to account' },
  ];

  return (
    <DropdownPanel visible={visible} onDismiss={onDismiss}>
      <View style={styles.identity}>
        <View style={styles.avatar}>
          <IconUser size={26} sw={2} color={Colors.light.card} />
        </View>
        <View style={styles.identityText}>
          <Text style={styles.handle} numberOfLines={1}>
            {handle ? `@${handle}` : '@User'}
          </Text>
          <Text style={styles.userId} numberOfLines={1}>
            {handle ? `ID: @${handle}` : 'ID: @user…'}
          </Text>
        </View>
      </View>

      {actions.map((item) => (
        <PanelRow key={item.key} item={item} />
      ))}

      {handle ? null : (
        <Pressable
          onPress={onSignIn}
          disabled={signingIn}
          style={({ pressed }) => [styles.signIn, pressed && styles.pressed]}
          accessibilityRole="button"
        >
          {signingIn ? (
            <ActivityIndicator size="small" color={Colors.light.accent} />
          ) : (
            <>
              {/* O "G" colorido do Google é marca registrada; o SVG oficial
                  entra junto com o botão do próprio SDK, não desenhado à mão. */}
              <Text style={styles.googleMark}>G</Text>
              <Text style={styles.signInLabel}>Sign in with Google</Text>
            </>
          )}
        </Pressable>
      )}
    </DropdownPanel>
  );
}

const styles = StyleSheet.create({
  identity: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two + 2 },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  identityText: { flex: 1 },
  handle: { fontFamily: Fonts.bold, fontSize: 16, color: Colors.light.ink },
  userId: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 1 },

  signIn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two - 2,
    height: 36,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.accentSoft,
    marginTop: Spacing.one,
  },
  googleMark: { fontFamily: Fonts.bold, fontSize: 15, color: '#4285F4' },
  signInLabel: { fontFamily: Fonts.bold, fontSize: 12, color: Colors.light.ink },
  pressed: { opacity: 0.6 },
});
