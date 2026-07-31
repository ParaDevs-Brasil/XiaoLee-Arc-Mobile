import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

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
  onSignIn?: () => void;
}

/**
 * As seis ações do frame. As três primeiras já têm destino; `connect`,
 * `withdraw` e `deposit` continuam inertes porque dependem de um conector de
 * carteira que o mobile não tem — o web usa extensão de navegador
 * (EIP-6963/Freighter), sem equivalente aqui sem WalletConnect.
 */
const ACTIONS: (PanelItem & { href?: '/wallet' | '/transactions' | '/history' })[] = [
  { key: 'wallet', Icon: IconWallet, title: 'wallet', subtitle: 'View token balance', href: '/wallet' },
  {
    key: 'transaction',
    Icon: IconClipboard,
    title: 'Transaction',
    subtitle: 'View swap history',
    href: '/transactions',
  },
  {
    key: 'history',
    Icon: IconClock,
    title: 'History',
    subtitle: 'View conversations and activities',
    href: '/history',
  },
  {
    key: 'connect',
    Icon: IconClipboard,
    title: 'Connect Wallet',
    subtitle: 'ARC - Solana - Stellar - USDC',
  },
  { key: 'withdraw', Icon: IconDownload, title: 'Withdraw', subtitle: 'Withdraw funds to wallet' },
  { key: 'deposit', Icon: IconUpload, title: 'Deposit', subtitle: 'Add funds to account' },
];

export function ProfileMenu({ visible, onDismiss, handle, onSignIn }: ProfileMenuProps) {
  const router = useRouter();

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

      {ACTIONS.map(({ href, ...item }) => (
        <PanelRow
          key={item.key}
          item={{
            ...item,
            // `push` e não `navigate`: a carteira é destino lateral, e o voltar
            // do Android deve devolver o usuário à tela de onde ele abriu o
            // painel — mesma escolha do sino no `ScreenShell`.
            onPress: href
              ? () => {
                  onDismiss();
                  router.push(href);
                }
              : undefined,
          }}
        />
      ))}

      <Pressable
        onPress={onSignIn}
        style={({ pressed }) => [styles.signIn, pressed && styles.pressed]}
        accessibilityRole="button"
      >
        {/* O "G" colorido do Google é marca registrada; o SVG oficial entra
            junto com o botão real de login, não como aproximação desenhada. */}
        <Text style={styles.googleMark}>G</Text>
        <Text style={styles.signInLabel}>Sign in with Google</Text>
      </Pressable>
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
