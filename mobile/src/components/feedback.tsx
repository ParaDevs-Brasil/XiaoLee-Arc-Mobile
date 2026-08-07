import { useEffect, useState } from 'react';
import type { DimensionValue, StyleProp, ViewStyle } from 'react-native';
import { ActivityIndicator, Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';

import type { IconProps } from '@/components/icons';
import { IconWallet } from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { useWalletConnect } from '@/lib/walletconnect';

/**
 * Os três estados que toda tela de dado tem antes (ou em vez) do conteúdo:
 * carregando, vazio e falha.
 *
 * Ficam juntos de propósito — são excludentes entre si e as telas escolhem um
 * dos três no mesmo ponto do render.
 */

/** Primeira carga. Para recarga com dado na tela, use o `RefreshControl`. */
export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <View style={styles.centered}>
      <ActivityIndicator color={Colors.light.accent} />
      <Text style={styles.dim}>{label}</Text>
    </View>
  );
}

export function EmptyState({
  Icon,
  title,
  text,
  action,
}: {
  Icon: (p: IconProps) => React.ReactElement;
  title: string;
  text: string;
  /** Saída do estado vazio, quando existe uma — um `SignInButton`, por exemplo. */
  action?: React.ReactNode;
}) {
  return (
    <View style={styles.centered}>
      <View style={styles.emptyIcon}>
        <Icon size={22} color={Colors.light.ink3} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.dim}>{text}</Text>
      {action}
    </View>
  );
}

/**
 * Bloco cinza pulsante com a forma do conteúdo que ainda vai chegar.
 *
 * Serve de alternativa ao `LoadingState` nas telas cujo conteúdo tem silhueta
 * previsível: o spinner centralizado ocupa uma altura que não é a do resultado,
 * então a tela inteira salta quando o dado entra. Um esqueleto com a forma
 * certa segura o layout parado.
 *
 * Usa o `Animated` do React Native, e não o Reanimated, pelo mesmo motivo que
 * `dropdown-panel`: é o que o resto do app usa.
 */
export function Skeleton({
  height,
  width,
  radius = Radius.md,
  style,
}: {
  height: number;
  /** Sem largura o bloco estica na coluna, que é o caso comum. */
  width?: DimensionValue;
  radius?: number;
  style?: StyleProp<ViewStyle>;
}) {
  // A `Animated.Value` nasce uma vez e sobrevive aos re-renders — mesmo idioma
  // do `dropdown-panel`.
  const [pulse] = useState(() => new Animated.Value(0));

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 700,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    // Sem o `stop` a animação continua rodando depois que o dado chega e o
    // esqueleto sai da árvore.
    return () => loop.stop();
  }, [pulse]);

  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.4, 1] });

  return (
    <Animated.View
      style={[styles.skeleton, { height, width, borderRadius: radius }, style, { opacity }]}
    />
  );
}

/**
 * Falha de rede ou de API. `message` vem do `ApiError`, que já normaliza tanto
 * o `detail` do FastAPI quanto o timeout do cliente numa frase legível.
 */
export function ErrorState({
  title = "Couldn't load",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <View style={styles.error}>
      <Text style={styles.errorTitle}>{title}</Text>
      <Text style={styles.errorText}>{message}</Text>
      {onRetry ? (
        <Pressable
          onPress={onRetry}
          style={({ pressed }) => [styles.retry, pressed && styles.pressed]}
          accessibilityRole="button"
        >
          <Text style={styles.retryText}>Try again</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

/**
 * Conectar carteira de dentro do estado de convidado.
 *
 * Os estados vazios mandavam o usuário "para o chat", onde conectar não está à
 * vista: o botão mora no painel de perfil, atrás do avatar do header.
 * Instrução que aponta para lugar nenhum visível não é instrução — este botão
 * abre o modal no lugar onde o usuário já está.
 *
 * Sem `busy`/`error` próprios: `openModal()` só abre a UI nativa do
 * WalletConnect, que tem seus próprios estados — não há chamada de rede daqui
 * para esperar ou que possa falhar.
 */
export function ConnectWalletButton({ label = 'Connect Wallet' }: { label?: string }) {
  const { openModal } = useWalletConnect();

  return (
    <Pressable
      onPress={openModal}
      style={({ pressed }) => [styles.signIn, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <IconWallet size={16} color={Colors.light.card} />
      <Text style={styles.signInText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centered: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.five },
  dim: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    lineHeight: 20,
    color: Colors.light.ink2,
    textAlign: 'center',
  },
  emptyIcon: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.bg,
  },
  emptyTitle: { fontFamily: Fonts.semibold, fontSize: 14, color: Colors.light.ink },

  skeleton: { backgroundColor: Colors.light.border },

  error: {
    gap: Spacing.two,
    padding: Spacing.three - 2,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.dangerSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.danger,
  },
  errorTitle: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.danger },
  errorText: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 20, color: Colors.light.ink2 },
  retry: {
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two - 2,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.danger,
  },
  retryText: { fontFamily: Fonts.semibold, fontSize: 12, color: Colors.light.card },
  pressed: { opacity: 0.65 },

  // Sem `marginTop`: todos os pais que o usam já separam por `gap`, e a margem
  // extra desalinharia o botão quando ele entra numa linha, como no banner da
  // Campaigns.
  signIn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two - 2,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accent,
  },
  signInText: { fontFamily: Fonts.bold, fontSize: 13, color: Colors.light.card },
});
