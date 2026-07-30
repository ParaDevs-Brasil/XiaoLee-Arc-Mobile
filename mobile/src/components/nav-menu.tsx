import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { DropdownPanel } from '@/components/dropdown-panel';
import { IconBarChart, IconDollar, IconRocket } from '@/components/icons';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Menu de navegação — frame "Xiaolee - menu" (grupo `Group 9`, 191x264).
 *
 * Só três destinos, com o título maior (16 w700) e sem descrição — é a
 * diferença visual em relação ao painel de perfil.
 */

interface NavMenuProps {
  visible: boolean;
  onDismiss: () => void;
}

export function NavMenu({ visible, onDismiss }: NavMenuProps) {
  const router = useRouter();

  // Campaigns ainda não tem rota; navegar agora daria erro de rota
  // inexistente. Dashboard segue apontando para o diagnóstico até a tela
  // própria existir.
  const items = [
    { key: 'dashboard', Icon: IconBarChart, label: 'Dashboard', href: '/diagnostics' as const },
    { key: 'traction', Icon: IconDollar, label: 'Traction', href: '/traction' as const },
    { key: 'campaigns', Icon: IconRocket, label: 'Campaigns', href: null },
  ];

  return (
    <DropdownPanel visible={visible} onDismiss={onDismiss}>
      {items.map(({ key, Icon, label, href }) => (
        <View key={key} style={styles.row}>
          <View style={styles.icon}>
            <Icon size={20} color={Colors.light.accent} />
          </View>
          <Text
            style={styles.label}
            onPress={() => {
              onDismiss();
              if (href) router.push(href);
            }}
          >
            {label}
          </Text>
        </View>
      ))}
    </DropdownPanel>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two + 2, paddingVertical: 2 },
  icon: {
    width: 36,
    height: 36,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
  },
  label: { flex: 1, fontFamily: Fonts.bold, fontSize: 16, color: Colors.light.ink },
});
