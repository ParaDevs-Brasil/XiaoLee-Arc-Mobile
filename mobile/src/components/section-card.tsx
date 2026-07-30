import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Cartão de seção — mesma anatomia do card do chat (`app/index.tsx`): borda de
 * um fio, raio 16 e um cabeçalho separado do corpo por uma linha.
 *
 * `overflow: 'hidden'` é o que faz o conteúdo respeitar o raio nos cantos;
 * sem ele uma lista com fundo próprio vaza pelas quinas no Android.
 */

interface SectionCardProps {
  title: string;
  subtitle?: string;
  /** Canto direito do cabeçalho — normalmente um botão de recarregar. */
  action?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, subtitle, action, children }: SectionCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        {action}
      </View>

      <View style={styles.body}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    overflow: 'hidden',
    ...CardShadow,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.light.border,
  },
  headerText: { flex: 1 },
  title: { fontFamily: Fonts.bold, fontSize: 15, color: Colors.light.ink },
  subtitle: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.ink2, marginTop: 1 },
  body: { padding: Spacing.two + 2, gap: Spacing.two },
});
