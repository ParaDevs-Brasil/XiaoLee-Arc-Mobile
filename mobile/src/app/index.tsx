import { Image } from 'expo-image';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
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
import { appendChatMessage } from '@/lib/chat-history';

import { AnimatedAvatar } from '@/components/animated-avatar';
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
import { ScreenShell } from '@/components/screen-shell';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { useKeyboard } from '@/hooks/use-keyboard';

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
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  // Barra de gestos do Android come a margem de baixo do card sem este inset.
  const insets = useSafeAreaInsets();
  const keyboard = useKeyboard();
  const scroller = useRef<ScrollView>(null);

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;

    setDraft('');
    setSending(true);
    setMessages((current) => [
      ...current,
      { id: `u${Date.now()}`, author: 'user', text: message, time: now() },
    ]);
    // Fora do estado da tela, de propósito: o backend nunca grava conversa
    // (`campaigns_routes.py:557` devolve `chat_history` vazio fixo), então sem
    // isto a tela de Histórico não teria o que mostrar — mesmo acordo do web,
    // que grava no `localStorage` em vez de esperar o backend (`lib/chat-history.ts`).
    // Nunca rejeita, então não precisa de `catch` aqui.
    appendChatMessage('user', message);
    // Enquanto pensa, a personagem pensa junto.
    avatarAnimation.play('xiaolee_thinklow');

    try {
      const result = await sendChatMessage({ message });
      const reply = result.response?.[0]?.content?.trim() || 'Não consegui formular uma resposta agora.';

      setMessages((current) => [
        ...current,
        { id: `x${Date.now()}`, author: 'xiaolee', text: reply, time: now() },
      ]);
      // O texto gravado é o mesmo que foi para a bolha, fallback incluído —
      // o histórico não deve divergir do que a tela mostrou.
      appendChatMessage('assistant', reply);

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
      // O web também grava o texto de erro (`ChatPanel.tsx:256`) — uma
      // conversa que travou continua sendo conversa.
      appendChatMessage('assistant', detail);
      avatarAnimation.play('xiaolee_ouch');
    } finally {
      setSending(false);
    }
  }

  const empty = messages.length === 0;

  return (
    <ScreenShell>
      <KeyboardAvoidingView
        style={styles.flex}
        /**
         * `padding` nas duas plataformas — no Android também, apesar de a doc
         * da Expo mandar passar `undefined` lá.
         *
         * Aquele conselho é anterior ao edge-to-edge. Com `undefined` o
         * componente cai no `default` do `render()` e devolve uma `View` comum
         * (`KeyboardAvoidingView.js:286`): ele calcula a altura do teclado e
         * não aplica em nada. Quem levantava o composer era o SO encolhendo a
         * janela por `adjustResize`. Desde o SDK 54 o edge-to-edge é
         * obrigatório e a janela não encolhe mais — o app desenha atrás do
         * teclado, então o rodapé ficava coberto.
         *
         * O ramo `padding` não depende disso: ele mede pelo `endCoordinates` do
         * evento `keyboardDidShow`, que o Android continua emitindo.
         *
         * Sem `keyboardVerticalOffset` de propósito: a conta do componente
         * mistura o `y` do layout com o `screenY` do teclado, o que só fecha se
         * a raiz React começar no topo da tela — e começa, porque esta tela roda
         * com `headerShown: false` (ver `_layout.tsx`) e o header é nosso.
         */
        behavior="padding"
      >
        {/* O inset de baixo só vale com o teclado fechado. Ele existe para o
            card não encostar na barra de gestos — mas o teclado cobre essa
            barra, e aí o `insets.bottom` deixa de proteger de alguma coisa e
            vira folga entre o composer e as teclas (no iOS somada à altura do
            teclado, que o `KeyboardAvoidingView` já empurrou). */}
        <View
          style={[
            styles.card,
            { marginBottom: Spacing.three - 4 + (keyboard.visible ? 0 : insets.bottom) },
          ]}
        >
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
            sending={sending}
          />
        </View>
      </KeyboardAvoidingView>
    </ScreenShell>
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
  sending,
}: {
  value: string;
  onChange: (next: string) => void;
  onSend: () => void;
  /** O agente está respondendo — diferente de "não há o que enviar". */
  sending: boolean;
}) {
  const canSend = value.trim().length > 0 && !sending;

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
        editable={!sending}
        /**
         * Sem isto o `onSubmitEditing` abaixo é prop morta: num campo
         * `multiline` o RN resolve `submitBehavior` para `'newline'`
         * (`TextInput.js:567`), então a tecla de retorno insere quebra de linha
         * e o handler nunca dispara — era o caso aqui.
         *
         * `'submit'` e não `'blurAndSubmit'`: envia **sem** tirar o foco, então
         * dá para emendar a próxima mensagem sem reabrir o teclado. O texto
         * ainda quebra sozinho e o campo cresce até `maxHeight`; o que se perde
         * é a quebra manual, que num chat com o agente quase não aparece.
         */
        submitBehavior="submit"
        // A tecla passa a se chamar "send" — ela envia, então deve dizer isso.
        returnKeyType="send"
        onSubmitEditing={onSend}
      />
      <Pressable
        onPress={onSend}
        disabled={!canSend}
        style={({ pressed }) => [
          styles.sendButton,
          // Esmaece só quando não há o que enviar. Enquanto o agente responde o
          // botão fica cheio com o spinner: esmaecido ele leria como desligado,
          // e não é isso — está trabalhando.
          !canSend && !sending && styles.sendButtonIdle,
          pressed && styles.pressed,
        ]}
        accessibilityRole="button"
        accessibilityLabel={sending ? 'Sending' : 'Send'}
        accessibilityState={{ disabled: !canSend, busy: sending }}
      >
        {/* A resposta depende de uma chamada a LLM, com timeout de 60s
            (`api/backend.ts`). Um botão parado nesse intervalo não distingue
            "mandei" de "não pegou". */}
        {sending ? (
          <ActivityIndicator size="small" color={Colors.light.card} />
        ) : (
          <IconSend size={18} color={Colors.light.card} />
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
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
    // Android centraliza o texto de um campo multiline na altura disponível, e
    // aí a segunda linha empurra a primeira para cima em vez de o texto crescer
    // para baixo. Mesmo ajuste do formulário de campanha (`campaigns/new.tsx`).
    textAlignVertical: 'top',
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
