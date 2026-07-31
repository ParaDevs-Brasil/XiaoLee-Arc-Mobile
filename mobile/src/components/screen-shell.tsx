import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { HeaderBar } from '@/components/header-bar';
import { NavMenu } from '@/components/nav-menu';
import { ProfileMenu } from '@/components/profile-menu';
import { Colors, Fonts, Spacing } from '@/constants/theme';

/**
 * Moldura comum a todas as telas: a barra do topo e os dois painéis que ela
 * abre.
 *
 * Isto vivia inline no chat. Com mais de uma tela cada uma repetiria o mesmo
 * estado de painel e a mesma ordem de renderização — e a ordem importa: os
 * painéis vêm **depois** do conteúdo para ficarem por cima dele, como nos
 * frames do Figma. Centralizar também garante que ligar o sino uma vez o
 * ligue em todas as telas.
 */

/** Qual painel do header está aberto — só um por vez, como no Figma. */
type OpenPanel = 'none' | 'menu' | 'profile';

export function ScreenShell({ children }: { children: ReactNode }) {
  const [panel, setPanel] = useState<OpenPanel>('none');
  const router = useRouter();

  const close = () => setPanel('none');
  /** Tocar no mesmo ícone fecha; nos dois painéis, abrir um fecha o outro. */
  const toggle = (next: Exclude<OpenPanel, 'none'>) =>
    setPanel((current) => (current === next ? 'none' : next));

  return (
    <View style={styles.screen}>
      <HeaderBar
        // `push` e não `navigate`: notificações é um destino lateral, e o
        // voltar do Android deve devolver o usuário à tela de onde ele tocou
        // no sino, não à raiz.
        onPressNotifications={() => {
          close();
          router.push('/notifications');
        }}
        onPressMenu={() => toggle('menu')}
        onPressProfile={() => toggle('profile')}
        // `navigate` e não `push`: o chat é a raiz da pilha, então empilhar
        // uma segunda cópia dele deixaria o voltar do Android preso num
        // vaivém entre dois chats idênticos.
        onPressLogo={() => router.navigate('/')}
      />

      {children}

      <NavMenu visible={panel === 'menu'} onDismiss={close} />
      <ProfileMenu visible={panel === 'profile'} onDismiss={close} />
    </View>
  );
}

/**
 * Título e linha de apoio no topo do conteúdo — o bloco centralizado que o
 * web repete em Traction, Campaigns, Dashboard e Notifications.
 */
export function PageHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <View style={styles.heading}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.subtitle}>{subtitle}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.light.bg },
  heading: { alignItems: 'center', gap: Spacing.two - 2 },
  title: { fontFamily: Fonts.bold, fontSize: 24, color: Colors.light.ink },
  subtitle: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 21,
    color: Colors.light.ink2,
    textAlign: 'center',
  },
});
