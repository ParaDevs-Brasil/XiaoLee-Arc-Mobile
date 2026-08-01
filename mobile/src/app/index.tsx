import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
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

import { sendChatMessage } from '@/api/backend';
import { ApiError } from '@/api/client';
import {
  animationFromBackend,
  avatarAnimation,
  type AnimationKey,
} from '@/lib/avatar-animation';
import { GoogleSignInCancelled, signInAndStartSession } from '@/lib/auth';
import { getSession, getWallet } from '@/lib/session';
import { useWalletConnect } from '@/lib/walletconnect';

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
import { ConnectWalletSheet } from '@/components/connect-wallet-sheet';
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
  /** O que é enviado ao agente ao tocar — o card é um atalho de conversa. */
  prompt: string;
}

const ACTIONS: Action[] = [
  {
    key: 'campaign',
    Icon: IconGift,
    title: 'Create a campaign',
    subtitle: 'Reward your community',
    prompt: 'I want to create a campaign to reward my community',
  },
  {
    key: 'dashboard',
    Icon: IconActivity,
    title: 'View dashboard',
    subtitle: 'Metrics and activity',
    prompt: 'Show me the dashboard metrics',
  },
  {
    key: 'swap',
    Icon: IconSwap,
    title: 'Make a swap',
    subtitle: 'Exchange tokens by chat',
    prompt: 'I want to make a swap',
  },
  {
    key: 'balance',
    Icon: IconWallet,
    title: 'Check balance',
    subtitle: 'See your wallet funds',
    prompt: 'What is my balance?',
  },
];

const SUGGESTIONS = [
  'What can you do for me?',
  'How do campaigns work?',
  'Show my recent transactions',
];

/** Qual painel do header está aberto — só um por vez, como no Figma. */
type OpenPanel = 'none' | 'menu' | 'profile';

interface Message {
  id: string;
  author: 'user' | 'xiaolee';
  text: string;
  /** Mesmo formato do web: `toLocaleTimeString` com hora e minuto. */
  time: string;
}

function now(): string {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Reações do rodapé da bolha — no web elas não registram nada, apenas fazem a
 * personagem reagir. É personalidade, não telemetria.
 */
const REACTIONS: { emoji: string; key: AnimationKey; label: string }[] = [
  { emoji: '💕', key: 'xiaolee_love', label: 'Love it!' },
  { emoji: '👏', key: 'xiaolee_cheer', label: 'Cool!' },
  { emoji: '😊', key: 'xiaolee_giggle', label: 'Funny!' },
];

export default function ChatScreen() {
  const [draft, setDraft] = useState('');
  const [panel, setPanel] = useState<OpenPanel>('none');
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [handle, setHandle] = useState<string>();
  const [wallet, setWallet] = useState<string>();
  const [signingIn, setSigningIn] = useState(false);
  const [walletSheet, setWalletSheet] = useState(false);
  // Barra de gestos do Android come a margem de baixo do card sem este inset.
  const insets = useSafeAreaInsets();
  const scroller = useRef<ScrollView>(null);

  // WalletConnect sincroniza endereço automaticamente
  const wc = useWalletConnect();

  const close = () => setPanel('none');
  /** Tocar no mesmo ícone fecha; nos dois painéis, abrir um fecha o outro. */
  const toggle = (next: Exclude<OpenPanel, 'none'>) =>
    setPanel((current) => (current === next ? 'none' : next));

  // Sessão e carteira sobrevivem ao fechamento do app (SecureStore), então o
  // estado é restaurado na montagem em vez de começar deslogado.
  useEffect(() => {
    let cancelled = false;
    Promise.all([getSession(), getWallet()]).then(([session, stored]) => {
      if (cancelled) return;
      if (session?.twitterUserId) setHandle(session.twitterUserId);
      if (stored) setWallet(stored.address);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Mantém wallet em sync com WalletConnect
  useEffect(() => {
    if (wc.isConnected && wc.address) {
      setWallet(wc.address);
    }
  }, [wc.isConnected, wc.address]);

  async function signIn() {
    setSigningIn(true);
    try {
      const session = await signInAndStartSession();
      setHandle(session.twitterUserId);
      close();
    } catch (error) {
      // Desistir do login não é erro — não vale poluir a conversa com isso.
      if (error instanceof GoogleSignInCancelled) return;
      const detail = error instanceof ApiError ? error.message : String(error);
      setMessages((current) => [
        ...current,
        { id: `e${Date.now()}`, author: 'xiaolee', text: detail, time: now() },
      ]);
    } finally {
      setSigningIn(false);
    }
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;

    setDraft('');
    setSending(true);
    setMessages((current) => [
      ...current,
      { id: `u${Date.now()}`, author: 'user', text: message, time: now() },
    ]);
    // Enquanto pensa, a personagem pensa junto.
    avatarAnimation.play('xiaolee_thinklow');

    try {
      // Mesmo contexto que o web manda em cada mensagem: sem isso o agente
      // não sabe qual carteira consultar e responde "conecte sua carteira".
      const wallet = await getWallet();
      const result = await sendChatMessage({
        message,
        ...(wallet && { wallet_address: wallet.address, wallet_chain: wallet.chain }),
      });
      const reply = result.response?.[0]?.content?.trim();

      setMessages((current) => [
        ...current,
        {
          id: `x${Date.now()}`,
          author: 'xiaolee',
          text: reply || 'Não consegui formular uma resposta agora.',
          time: now(),
        },
      ]);

      // O agente escolhe a emoção; nome desconhecido volta para o idle.
      const animation = animationFromBackend(result.animations);
      if (animation) avatarAnimation.play(animation);
      else avatarAnimation.expressionEnded();
    } catch (error) {
      const detail = error instanceof ApiError ? error.message : String(error);
      setMessages((current) => [
        ...current,
        { id: `e${Date.now()}`, author: 'xiaolee', text: detail, time: now() },
      ]);
      avatarAnimation.play('xiaolee_ouch');
    } finally {
      setSending(false);
    }
  }

  const empty = messages.length === 0;

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
          {/* Na conversa o hero some, então a personagem passa a viver aqui —
              sempre há exatamente uma avatar animada, e as reações têm onde
              acontecer. */}
          <AssistantHeader animated={!empty} />

          <ScrollView
            ref={scroller}
            contentContainerStyle={empty ? styles.body : styles.thread}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            onContentSizeChange={() => scroller.current?.scrollToEnd({ animated: true })}
          >
            {empty ? (
              <>
                {/* Animado só aqui. O avatar de 40dp do header ficaria com um
                    segundo decoder na mesma tela por ganho quase nulo. */}
                <AnimatedAvatar size={104} />

                <Text style={styles.greeting}>Hi! I&apos;m Xiaolee ✨</Text>
                <Text style={styles.pitch}>
                  Swaps, campaigns and payments — all by message. What would you like to do?
                </Text>

                <View style={styles.actions}>
                  {ACTIONS.map((action) => (
                    <ActionCard key={action.key} action={action} onPress={() => send(action.prompt)} />
                  ))}
                </View>

                <View style={styles.suggestions}>
                  {SUGGESTIONS.map((text) => (
                    <Suggestion key={text} text={text} onPress={() => send(text)} />
                  ))}
                </View>
              </>
            ) : (
              <>
                {messages.map((message) => (
                  <Bubble key={message.id} message={message} />
                ))}
                {sending ? <Typing /> : null}
              </>
            )}
          </ScrollView>

          <Composer
            value={draft}
            onChange={setDraft}
            onSend={() => send(draft)}
            disabled={sending}
          />
        </View>
      </KeyboardAvoidingView>

      {/* Depois do card para ficarem por cima dele, como nos frames do Figma. */}
      <NavMenu visible={panel === 'menu'} onDismiss={close} />
      <ProfileMenu
        visible={panel === 'profile'}
        onDismiss={close}
        handle={handle}
        walletAddress={wallet}
        signingIn={signingIn}
        onSignIn={signIn}
        onConnectWallet={() => setWalletSheet(true)}
      />
      <ConnectWalletSheet
        visible={walletSheet}
        onClose={() => setWalletSheet(false)}
        onConnected={setWallet}
      />
    </View>
  );
}

/**
 * Bolha de mensagem — mesma anatomia do `ChatPanel.tsx` do web: canto da
 * "cauda" reduzido do lado de quem fala, largura máxima de 85%, e um rodapé
 * com autor e horário. Na fala da Xiaolee, avatar à esquerda e as reações.
 */
function Bubble({ message }: { message: Message }) {
  const mine = message.author === 'user';

  if (mine) {
    return (
      <View style={styles.rowUser}>
        <View style={styles.bubbleWrap}>
          <View style={[styles.bubble, styles.bubbleUser]}>
            <Text style={styles.bubbleTextUser}>{message.text}</Text>
          </View>
          {/* Separador só quando há hora, como no web — sem isso sobra um
              "You ·" pendurado se a mensagem vier sem timestamp. */}
          <Text style={styles.metaRight}>You{message.time ? ` · ${message.time}` : ''}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.rowXiaolee}>
      <Image
        source={require('../../assets/images/xiaolee-avatar.png')}
        style={styles.msgAvatar}
        contentFit="cover"
      />
      <View style={styles.bubbleWrap}>
        <View style={[styles.bubble, styles.bubbleXiaolee]}>
          <Text style={styles.bubbleText}>{message.text}</Text>
        </View>
        <View style={styles.meta}>
          <Text style={styles.metaText}>Xiaolee{message.time ? ` · ${message.time}` : ''}</Text>
          <View style={styles.reactions}>
            {REACTIONS.map(({ emoji, key, label }) => (
              <Pressable
                key={emoji}
                onPress={() => avatarAnimation.play(key)}
                accessibilityRole="button"
                accessibilityLabel={label}
                hitSlop={Spacing.two}
              >
                <Text style={styles.reaction}>{emoji}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </View>
  );
}

/** Três pontos enquanto o agente responde, como no web (sem rodapé). */
function Typing() {
  return (
    <View style={styles.rowXiaolee}>
      {/* Sem o deslocamento das mensagens normais: aqui não há rodapé de
          horário para compensar, e o offset deixaria o avatar solto acima. */}
      <Image
        source={require('../../assets/images/xiaolee-avatar.png')}
        style={[styles.msgAvatar, styles.msgAvatarTyping]}
        contentFit="cover"
      />
      <View style={[styles.bubble, styles.bubbleXiaolee, styles.typing]}>
        {[0, 1, 2].map((i) => (
          <View key={i} style={styles.dot} />
        ))}
      </View>
    </View>
  );
}

/** Faixa de identidade do assistente, fixa no topo do card. */
function AssistantHeader({ animated }: { animated: boolean }) {
  return (
    <View style={styles.assistant}>
      <View>
        {animated ? (
          <AnimatedAvatar size={40} />
        ) : (
          <Image
            source={require('../../assets/images/xiaolee-avatar.png')}
            style={styles.assistantAvatar}
            contentFit="cover"
          />
        )}
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

function ActionCard({
  action: { Icon, title, subtitle },
  onPress,
}: {
  action: Action;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
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

function Composer({
  value,
  onChange,
  onSend,
  disabled,
}: {
  value: string;
  onChange: (next: string) => void;
  onSend: () => void;
  disabled: boolean;
}) {
  const canSend = value.trim().length > 0 && !disabled;

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
        editable={!disabled}
        onSubmitEditing={onSend}
      />
      <Pressable
        onPress={onSend}
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

  // ── Conversa ───────────────────────────────────────────────────────────
  thread: {
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.three,
    gap: Spacing.three - 4,
  },
  rowUser: { flexDirection: 'row', justifyContent: 'flex-end' },
  rowXiaolee: { flexDirection: 'row', alignItems: 'flex-end', gap: Spacing.two },
  bubbleWrap: { maxWidth: '85%' },
  msgAvatar: {
    width: 28,
    height: 28,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.bg,
    // Sobe o avatar a altura do rodapé (10px + marginTop 4) para o alinhamento
    // ser com a base da bolha, não com a base da linha inteira.
    marginBottom: 18,
  },
  /** Linha de digitando não tem rodapé, então nada a compensar. */
  msgAvatarTyping: { marginBottom: 0 },
  bubble: {
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
    borderRadius: Radius.lg,
    ...CardShadow,
  },
  // Canto da "cauda" reduzido do lado de quem fala, como no web.
  bubbleUser: {
    backgroundColor: Colors.light.accent,
    borderBottomRightRadius: Radius.sm - 2,
  },
  bubbleXiaolee: {
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    borderBottomLeftRadius: Radius.sm - 2,
  },
  bubbleText: { fontFamily: Fonts.sans, fontSize: 14, lineHeight: 21, color: Colors.light.ink2 },
  bubbleTextUser: {
    fontFamily: Fonts.medium,
    fontSize: 14,
    lineHeight: 21,
    color: Colors.light.card,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: Spacing.one,
    paddingHorizontal: Spacing.one,
  },
  metaText: { fontFamily: Fonts.sans, fontSize: 10, color: Colors.light.ink3 },
  metaRight: {
    fontFamily: Fonts.sans,
    fontSize: 10,
    color: Colors.light.ink3,
    textAlign: 'right',
    marginTop: Spacing.one,
    paddingRight: Spacing.one,
  },
  reactions: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one + 2 },
  // Meia opacidade como no web — presentes, mas sem competir com o texto.
  reaction: { fontSize: 12, opacity: 0.5 },
  typing: { flexDirection: 'row', alignItems: 'center', gap: Spacing.one + 1 },
  dot: {
    width: 6,
    height: 6,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accent,
    opacity: 0.6,
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
