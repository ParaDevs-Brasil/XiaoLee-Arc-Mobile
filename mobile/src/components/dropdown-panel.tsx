import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { IconProps } from '@/components/icons';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Painel ancorado no header — a base dos frames "Xiaolee - menu" e
 * "Xiaolee - Profile" do Figma.
 *
 * Nos dois desenhos o painel não é uma tela: aparece por cima do chat, colado
 * no topo direito, com o conteúdo do chat visível atrás. Largura 191 vem do
 * arquivo (grupos `Group 9` e `menu-profile`).
 */

/** Largura dos dois painéis no Figma. */
const PANEL_WIDTH = 191;

interface DropdownPanelProps {
  visible: boolean;
  onDismiss: () => void;
  children: ReactNode;
}

export function DropdownPanel({ visible, onDismiss, children }: DropdownPanelProps) {
  const insets = useSafeAreaInsets();
  if (!visible) return null;

  return (
    // O backdrop cobre a tela inteira para capturar o toque de fechar; sem ele
    // o único jeito de sair seria tocando de novo no ícone que abriu.
    <Pressable style={styles.backdrop} onPress={onDismiss} accessibilityLabel="Fechar menu">
      <Pressable
        style={[styles.panel, { top: 53 + insets.top + Spacing.three - 4 }]}
        // Toque dentro do painel não deve fechá-lo.
        onPress={(event) => event.stopPropagation()}
      >
        {children}
      </Pressable>
    </Pressable>
  );
}

export interface PanelItem {
  key: string;
  Icon: (p: IconProps) => React.ReactElement;
  title: string;
  subtitle?: string;
  onPress?: () => void;
}

/** Linha do painel: ícone em quadrado suave + título e descrição opcional. */
export function PanelRow({ item: { Icon, title, subtitle, onPress } }: { item: PanelItem }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}. ${subtitle}` : title}
    >
      <View style={styles.rowIcon}>
        <Icon size={18} color={Colors.light.accent} />
      </View>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{title}</Text>
        {subtitle ? <Text style={styles.rowSubtitle}>{subtitle}</Text> : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, zIndex: 10 },
  panel: {
    position: 'absolute',
    right: Spacing.three - 4,
    width: PANEL_WIDTH,
    paddingVertical: Spacing.two + 2,
    paddingHorizontal: Spacing.two + 2,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    gap: Spacing.two + 2,
    ...CardShadow,
  },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two + 2 },
  rowIcon: {
    width: 34,
    height: 34,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
  },
  rowText: { flex: 1 },
  rowTitle: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.ink },
  rowSubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 9,
    lineHeight: 12,
    color: Colors.light.ink2,
    marginTop: 1,
  },
  pressed: { opacity: 0.6 },
});
