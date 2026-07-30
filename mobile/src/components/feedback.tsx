import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import type { IconProps } from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';

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
}: {
  Icon: (p: IconProps) => React.ReactElement;
  title: string;
  text: string;
}) {
  return (
    <View style={styles.centered}>
      <View style={styles.emptyIcon}>
        <Icon size={22} color={Colors.light.ink3} />
      </View>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.dim}>{text}</Text>
    </View>
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
});
