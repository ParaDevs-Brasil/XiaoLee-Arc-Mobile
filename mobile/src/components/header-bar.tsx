import { Pressable, StyleSheet, Text, View } from 'react-native';

import { IconBell, IconList, IconUser } from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Barra superior presente nas quatro telas do Figma ("Xiaolee - AI Chat",
 * Dashboard, Profile e menu) — sempre a mesma: wordmark à esquerda, sino,
 * hambúrguer e avatar à direita.
 *
 * Profile e menu não são telas separadas no desenho: são painéis ancorados
 * neste avatar e neste hambúrguer. Daí os callbacks em vez de navegação.
 */

interface HeaderBarProps {
  onPressNotifications?: () => void;
  onPressMenu?: () => void;
  onPressProfile?: () => void;
}

export function HeaderBar({
  onPressNotifications,
  onPressMenu,
  onPressProfile,
}: HeaderBarProps) {
  return (
    <View style={styles.bar}>
      {/* Wordmark: "Xiao" neutro + "lee" no acento, com o sparkle sobrescrito */}
      <Text style={styles.wordmark}>
        Xiao<Text style={styles.wordmarkAccent}>lee</Text>
        <Text style={styles.sparkle}> ✦</Text>
      </Text>

      <View style={styles.actions}>
        <Pressable
          onPress={onPressNotifications}
          hitSlop={Spacing.two}
          accessibilityRole="button"
          accessibilityLabel="Notificações"
        >
          <IconBell size={24} color={Colors.light.accent} />
        </Pressable>

        <Pressable
          onPress={onPressMenu}
          hitSlop={Spacing.two}
          accessibilityRole="button"
          accessibilityLabel="Menu"
        >
          <IconList size={26} color={Colors.light.accent} />
        </Pressable>

        {/* Avatar: círculo cheio no acento — um dos poucos usos permitidos */}
        <Pressable
          onPress={onPressProfile}
          hitSlop={Spacing.two}
          accessibilityRole="button"
          accessibilityLabel="Perfil"
          style={styles.avatar}
        >
          <IconUser size={18} sw={2} color={Colors.light.card} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    height: 53,
    paddingHorizontal: Spacing.two,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.light.card,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.light.border,
  },
  wordmark: {
    fontFamily: Fonts.bold,
    fontSize: 24,
    color: Colors.light.ink,
  },
  wordmarkAccent: {
    color: Colors.light.accent,
  },
  sparkle: {
    fontSize: 10,
    color: Colors.light.accent,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  avatar: {
    width: 30,
    height: 30,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
