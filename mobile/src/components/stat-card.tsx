import { StyleSheet, Text, View } from 'react-native';

import type { IconProps } from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Cartão de métrica — o bloco que o web repete no topo de Traction, Dashboard
 * e Notifications: ícone + rótulo em caixa alta, o número grande embaixo.
 *
 * O cartão em si é neutro. A regra de ouro do design system é que o acento só
 * aparece em botão primário, avatar e destaques, então aqui ele fica restrito
 * ao ícone — e por isso `tone` colore o ícone, nunca o fundo do cartão.
 */

export type StatTone = 'accent' | 'success' | 'neutral';

const TONE: Record<StatTone, { color: string; background: string }> = {
  accent: { color: Colors.light.accent, background: Colors.light.accentSoft },
  success: { color: Colors.light.success, background: Colors.light.successSoft },
  neutral: { color: Colors.light.ink2, background: Colors.light.bg },
};

interface StatCardProps {
  Icon: (p: IconProps) => React.ReactElement;
  label: string;
  value: string;
  /** Linha de contexto abaixo do número (ex.: "3 nas últimas 24h"). */
  sub?: string;
  tone?: StatTone;
}

export function StatCard({ Icon, label, value, sub, tone = 'accent' }: StatCardProps) {
  const { color, background } = TONE[tone];

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={[styles.icon, { backgroundColor: background }]}>
          <Icon size={14} color={color} />
        </View>
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
      </View>

      <Text style={styles.value} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.7}>
        {value}
      </Text>
      {sub ? <Text style={styles.sub}>{sub}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    // `flex: 1` + `minWidth` deixa dois por linha num wrap sem calcular
    // larguras: dois cabem, um terceiro quebra.
    flex: 1,
    minWidth: 140,
    gap: Spacing.two,
    padding: Spacing.three - 2,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 2 },
  icon: {
    width: 24,
    height: 24,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    flex: 1,
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
  },
  value: { fontFamily: Fonts.bold, fontSize: 24, color: Colors.light.ink },
  sub: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: -Spacing.one },
});
