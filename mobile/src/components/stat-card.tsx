import type { ReactNode } from 'react';
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
 *
 * Vêm duas formas: `StatCard`, que é a métrica de corpo do texto (e em `lg`
 * vira o número herói de uma tela), e `MiniStat`, que é a métrica de apoio.
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
  /**
   * `lg` é o número herói: ocupa a largura toda em vez de dividir a linha, e
   * existe para dar hierarquia a uma tela cuja métrica principal se perderia
   * numa grade de cartões do mesmo peso.
   */
  size?: 'md' | 'lg';
  /**
   * Rodapé do cartão — na prática um `Sparkline`. Fica como slot em vez de
   * prop de dados porque o cartão não deveria saber desenhar gráfico: ele
   * reserva o espaço, quem chama decide o que vai ali.
   */
  chart?: ReactNode;
}

export function StatCard({
  Icon,
  label,
  value,
  sub,
  tone = 'accent',
  size = 'md',
  chart,
}: StatCardProps) {
  const { color, background } = TONE[tone];
  const large = size === 'lg';

  return (
    <View style={[styles.card, large && styles.cardLg]}>
      <View style={styles.header}>
        <View style={[styles.icon, large && styles.iconLg, { backgroundColor: background }]}>
          <Icon size={large ? 17 : 14} color={color} />
        </View>
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
      </View>

      <Text
        style={[styles.value, large && styles.valueLg]}
        numberOfLines={1}
        adjustsFontSizeToFit
        minimumFontScale={0.7}
      >
        {value}
      </Text>
      {sub ? <Text style={styles.sub}>{sub}</Text> : null}
      {chart ? <View style={styles.chart}>{chart}</View> : null}
    </View>
  );
}

interface MiniStatProps {
  Icon: (p: IconProps) => React.ReactElement;
  label: string;
  value: string;
}

/**
 * Métrica de apoio — três por linha, ao lado de um `StatCard` em `lg`.
 *
 * A anatomia é outra, e não só o tamanho: a um terço da largura da tela não
 * cabe rótulo em caixa alta ao lado de um ícone, então aqui tudo empilha
 * centralizado. Os cartões alinham o conteúdo pelo topo de propósito — assim
 * os números ficam na mesma linha mesmo quando um rótulo quebra em duas.
 */
export function MiniStat({ Icon, label, value }: MiniStatProps) {
  return (
    <View style={styles.mini}>
      <Icon size={14} color={Colors.light.ink3} />
      <Text style={styles.miniValue} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.6}>
        {value}
      </Text>
      <Text style={styles.miniLabel} numberOfLines={2}>
        {label}
      </Text>
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
  // Fora de uma linha o `flex: 1` herdado faria o cartão esticar até o fim do
  // scroll; `alignSelf` devolve a largura cheia sem esticar a altura.
  cardLg: { flex: 0, alignSelf: 'stretch', padding: Spacing.three + 2 },
  header: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 2 },
  icon: {
    width: 24,
    height: 24,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconLg: { width: 30, height: 30, borderRadius: Radius.md },
  label: {
    flex: 1,
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
  },
  value: { fontFamily: Fonts.bold, fontSize: 24, color: Colors.light.ink },
  // 48 é o piso do número herói. Abaixo disso ele deixa de liderar a tela e
  // vira só mais um número grande.
  valueLg: { fontSize: 48, letterSpacing: -0.8 },
  sub: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: -Spacing.one },
  chart: { marginTop: Spacing.one },

  mini: {
    flex: 1,
    alignItems: 'center',
    gap: Spacing.one,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.two + 4,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  miniValue: { fontFamily: Fonts.bold, fontSize: 19, color: Colors.light.ink },
  miniLabel: {
    fontFamily: Fonts.bold,
    fontSize: 9,
    lineHeight: 12,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
    textAlign: 'center',
  },
});
