import { Image } from 'expo-image';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AnimatedAvatar } from '@/components/animated-avatar';
import { HeaderBar } from '@/components/header-bar';
import {
  IconActivity,
  IconChat,
  IconCheck,
  IconGift,
  IconSend,
  IconSwap,
  IconWallet,
  type IconProps,
} from '@/components/icons';
import { NavMenu } from '@/components/nav-menu';
import { ProfileMenu } from '@/components/profile-menu';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';

/**
 * Tela de chat — a home do app.
 *
 * Implementa o frame "Xiaolee - AI Chat" (412x915) do arquivo Figma
 * "Xiaolee-Mobile". Medidas tiradas do próprio arquivo: cards de ação 62 de
 * altura com gap 10, chips 30 com gap 8, card externo raio 16.
 *
 * O avatar é um frame estático de `xiaolee_standby.mov` — a personagem é
 * animada no produto (ver ACTION_VIDEO_MAP no backend), mas o desenho pede
 * um still e um vídeo em loop aqui custaria bateria por nada.
 */

interface Action {
  key: string;
  Icon: (p: IconProps) => React.ReactElement;
  title: string;
  subtitle: string;
}

const ACTIONS: Action[] = [
  { key: 'campaign', Icon: IconGift, title: 'Create a campaign', subtitle: 'Reward your community' },
  { key: 'dashboard', Icon: IconActivity, title: 'View dashboard', subtitle: 'Metrics and activity' },
  { key: 'swap', Icon: IconSwap, title: 'Make a swap', subtitle: 'Exchange tokens by chat' },
  { key: 'balance', Icon: IconWallet, title: 'Check balance', subtitle: 'See your wallet funds' },
];

const SUGGESTIONS = [
  'What can you do for me?',
  'How do campaigns work?',
  'Show my recent transactions',
];

/** Qual painel do header está aberto — só um por vez, como no Figma. */
type OpenPanel = 'none' | 'menu' | 'profile';

export default function ChatScreen() {
  const [draft, setDraft] = useState('');
  const [panel, setPanel] = useState<OpenPanel>('none');
  // Barra de gestos do Android come a margem de baixo do card sem este inset.
  const insets = useSafeAreaInsets();

  const close = () => setPanel('none');
  /** Tocar no mesmo ícone fecha; nos dois painéis, abrir um fecha o outro. */
  const toggle = (next: Exclude<OpenPanel, 'none'>) =>
    setPanel((current) => (current === next ? 'none' : next));

  return (
    <View style={styles.screen}>
      <HeaderBar
        onPressMenu={() => toggle('menu')}
        onPressProfile={() => toggle('profile')}
      />

      <KeyboardAvoidingView
        style={styles.flex}
        // Sem isto o teclado cobre o input — o iOS não recua a view sozinho.
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={[styles.card, { marginBottom: Spacing.three - 4 + insets.bottom }]}>
          <AssistantHeader />

          <ScrollView
            contentContainerStyle={styles.body}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {/* Animado só aqui. O avatar de 40dp do header ficaria com um
                segundo decoder na mesma tela por ganho quase nulo. */}
            <AnimatedAvatar size={104} />

            <Text style={styles.greeting}>Hi! I&apos;m Xiaolee ✨</Text>
            <Text style={styles.pitch}>
              Swaps, campaigns and payments — all by message. What would you like to do?
            </Text>

            <View style={styles.actions}>
              {ACTIONS.map((action) => (
                <ActionCard key={action.key} action={action} />
              ))}
            </View>

            <View style={styles.suggestions}>
              {SUGGESTIONS.map((text) => (
                <Suggestion key={text} text={text} onPress={() => setDraft(text)} />
              ))}
            </View>
          </ScrollView>

          <Composer value={draft} onChange={setDraft} />
        </View>
      </KeyboardAvoidingView>

      {/* Depois do card para ficarem por cima dele, como nos frames do Figma. */}
      <NavMenu visible={panel === 'menu'} onDismiss={close} />
      <ProfileMenu visible={panel === 'profile'} onDismiss={close} />
    </View>
  );
}

/** Faixa de identidade do assistente, fixa no topo do card. */
function AssistantHeader() {
  return (
    <View style={styles.assistant}>
      <View>
        <Image
          source={require('../../assets/images/xiaolee-avatar.png')}
          style={styles.assistantAvatar}
          contentFit="cover"
        />
        <View style={styles.onlineDot} />
      </View>

      <View style={styles.flex}>
        <View style={styles.assistantNameRow}>
          <Text style={styles.assistantName}>Xiaolee</Text>
          <View style={styles.onlineDotSmall} />
          <Text style={styles.onlineLabel}>ONLINE</Text>
        </View>
        <Text style={styles.assistantRole}>Your intelligent DeFi assistant</Text>
      </View>

      <View style={styles.verifiedBadge}>
        <IconCheck size={10} sw={2.4} color={Colors.light.success} />
      </View>
    </View>
  );
}

function ActionCard({ action: { Icon, title, subtitle } }: { action: Action }) {
  return (
    <Pressable
      style={({ pressed }) => [styles.action, pressed && styles.pressed]}
      accessibilityRole="button"
      accessibilityLabel={`${title}. ${subtitle}`}
    >
      <View style={styles.actionIcon}>
        <Icon size={20} color={Colors.light.accent} />
      </View>
      <View style={styles.flex}>
        <Text style={styles.actionTitle}>{title}</Text>
        <Text style={styles.actionSubtitle}>{subtitle}</Text>
      </View>
    </Pressable>
  );
}

function Suggestion({ text, onPress }: { text: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.chip, pressed && styles.pressed]}
      accessibilityRole="button"
    >
      <IconChat size={12} color={Colors.light.ink2} />
      <Text style={styles.chipText}>{text}</Text>
    </Pressable>
  );
}

function Composer({ value, onChange }: { value: string; onChange: (next: string) => void }) {
  const canSend = value.trim().length > 0;

  return (
    <View style={styles.composer}>
      <TextInput
        value={value}
        onChangeText={onChange}
        placeholder="Ask Xiaolee anything…"
        placeholderTextColor={Colors.light.ink3}
        style={styles.input}
        multiline
        maxLength={2000}
      />
      <Pressable
        disabled={!canSend}
        style={({ pressed }) => [
          styles.sendButton,
          !canSend && styles.sendButtonIdle,
          pressed && styles.pressed,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Enviar"
      >
        <IconSend size={18} color={Colors.light.card} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.light.bg },
  flex: { flex: 1 },

  card: {
    flex: 1,
    margin: Spacing.three - 4,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    overflow: 'hidden',
    ...CardShadow,
  },

  // ── Faixa do assistente ────────────────────────────────────────────────
  assistant: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two + 2,
    paddingHorizontal: Spacing.three - 3,
    paddingVertical: Spacing.two + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.light.border,
  },
  assistantAvatar: {
    width: 40,
    height: 40,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.bg,
  },
  onlineDot: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: 12,
    height: 12,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.success,
    borderWidth: 2,
    borderColor: Colors.light.card,
  },
  assistantNameRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one + 2 },
  assistantName: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.ink },
  onlineDotSmall: {
    width: 6,
    height: 6,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.success,
  },
  onlineLabel: {
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.8,
    color: Colors.light.success,
  },
  assistantRole: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.ink2, marginTop: 1 },
  verifiedBadge: {
    width: 28,
    height: 20,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.successSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.successBorder,
  },

  // ── Corpo ──────────────────────────────────────────────────────────────
  body: {
    paddingHorizontal: Spacing.four + 3,
    paddingTop: Spacing.four + 6,
    paddingBottom: Spacing.four,
    alignItems: 'center',
  },
  hero: {
    width: 104,
    height: 104,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.bg,
  },
  greeting: {
    fontFamily: Fonts.bold,
    fontSize: 16,
    color: Colors.light.ink,
    marginTop: Spacing.three,
  },
  pitch: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 23,
    color: Colors.light.ink2,
    textAlign: 'center',
    marginTop: Spacing.two,
  },

  // ── Cards de ação ──────────────────────────────────────────────────────
  actions: { alignSelf: 'stretch', gap: 10, marginTop: Spacing.four + 2 },
  action: {
    height: 62,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: Spacing.two + 2,
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    backgroundColor: Colors.light.card,
  },
  actionIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
  },
  actionTitle: { fontFamily: Fonts.semibold, fontSize: 14, color: Colors.light.ink },
  actionSubtitle: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.ink2, marginTop: 1 },

  // ── Chips de sugestão ──────────────────────────────────────────────────
  suggestions: { gap: Spacing.two, marginTop: Spacing.four, alignItems: 'center' },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two - 2,
    height: 30,
    paddingHorizontal: Spacing.three - 2,
    borderRadius: Radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    backgroundColor: Colors.light.card,
  },
  chipText: { fontFamily: Fonts.medium, fontSize: 12, color: Colors.light.ink2 },

  // ── Composer ───────────────────────────────────────────────────────────
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.two + 2,
    paddingHorizontal: Spacing.three - 3,
    paddingVertical: Spacing.two + 2,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.light.border,
  },
  input: {
    flex: 1,
    minHeight: 46,
    maxHeight: 120,
    paddingHorizontal: Spacing.three,
    paddingTop: 13,
    paddingBottom: 13,
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    fontFamily: Fonts.medium,
    fontSize: 14,
    color: Colors.light.ink,
  },
  sendButton: {
    width: 50,
    height: 42,
    borderRadius: Radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  sendButtonIdle: { opacity: 0.45 },
  pressed: { opacity: 0.65 },
});
