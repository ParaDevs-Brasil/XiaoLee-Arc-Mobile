import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { listCampaigns } from '@/api/backend';
import { CampaignCard } from '@/components/campaign-card';
import { EmptyState, ErrorState, Skeleton } from '@/components/feedback';
import {
  IconBell,
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconClock,
  IconMegaphone,
  IconPlus,
  IconRefresh,
  IconTarget,
} from '@/components/icons';
import { PageHeading, ScreenShell } from '@/components/screen-shell';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { useBackendData } from '@/hooks/use-backend-data';
import { useSession } from '@/hooks/use-session';

/**
 * Tela de Campaigns — porta de `frontend/src/pages/CampanhasNew.tsx`.
 *
 * Mantém a mesma anatomia do web: aviso de sessão, abas, "como funciona"
 * recolhível, contador com navegação e o carrossel de um cartão por vez. O
 * carrossel não é adaptação: o web já o desenhou pensando no mobile
 * ("um card por vez, swipe no mobile, snap").
 *
 * Só `GET /campaigns` é público. Entrar, verificar, resgatar e criar exigem
 * sessão, e o login do mobile (`lib/auth.ts`) ainda não está ligado a nenhuma
 * tela — daí a tela inteira renderizar no estado de convidado.
 */

/** Margem lateral do conteúdo; o cartão do carrossel é medido a partir dela. */
const H_PADDING = Spacing.three - 4;
const CARD_GAP = Spacing.three - 4;

type Tab = 'explore' | 'mine' | 'rewards';

export default function CampaignsScreen() {
  // Barra de gestos do Android come o fim da lista sem este inset.
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [tab, setTab] = useState<Tab>('explore');
  const [howOpen, setHowOpen] = useState(false);
  const [scrolledTo, setScrolledTo] = useState(0);
  const carousel = useRef<ScrollView>(null);

  // `listCampaigns` é função de módulo: identidade estável, sem recarga a cada
  // render.
  const { data, error, loading, refreshing, reload } = useBackendData(listCampaigns);
  const campaigns = data?.campaigns ?? [];

  // Lido do armazenamento, não fixo: hoje é sempre `false` porque nada grava
  // sessão ainda, mas no dia em que o login for ligado a tela inteira
  // acompanha sozinha — banner, aba e botões já dependem daqui.
  const { hasSession } = useSession();

  const cardWidth = width - H_PADDING * 2;
  const step = cardWidth + CARD_GAP;

  /**
   * A posição do carrossel é derivada, não lida direto do estado.
   *
   * A lista vem do backend e muda sozinha no refresh: quando uma campanha
   * encerra, o índice guardado passa a apontar para fora dela — o contador
   * mostrava "3/2", nenhum ponto ficava ativo e a seta esquerda continuava
   * habilitada apontando para o nada. Derivar corrige os três lugares de uma
   * vez, e sem escrever estado dentro de efeito, que o React Compiler trata
   * como render em cascata (ver `use-backend-data.ts`).
   */
  const index = Math.min(scrolledTo, Math.max(0, campaigns.length - 1));

  const goTo = (next: number) => {
    const clamped = Math.max(0, Math.min(next, campaigns.length - 1));
    carousel.current?.scrollTo({ x: clamped * step, animated: true });
    setScrolledTo(clamped);
  };

  return (
    <ScreenShell>
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: Spacing.four + insets.bottom }]}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={reload}
            tintColor={Colors.light.accent}
            colors={[Colors.light.accent]}
          />
        }
      >
        <PageHeading
          title="Campaigns"
          subtitle="Join campaigns on Arc Testnet and earn real rewards."
        />

        <SessionBanner hasSession={hasSession} />

        <TabBar
          tab={tab}
          onChange={setTab}
          exploreCount={campaigns.length}
          hasSession={hasSession}
        />

        <HowItWorks open={howOpen} onToggle={() => setHowOpen((v) => !v)} />

        {/* Aparece mesmo com lista na tela: uma recarga que falhou em silêncio
            faria campanhas encerradas passarem por abertas. */}
        {error ? (
          <ErrorState title="Error loading campaigns" message={error} onRetry={reload} />
        ) : null}

        {tab === 'explore' ? (
          <>
            {loading && !data ? <CampaignsSkeleton /> : null}

            {data && campaigns.length === 0 ? (
              <EmptyState
                Icon={IconMegaphone}
                title="No active campaigns"
                text="New campaigns coming soon. Check back in a moment."
              />
            ) : null}

            {campaigns.length > 0 ? (
              <>
                <View style={styles.listHeader}>
                  <Text style={styles.count}>
                    <Text style={styles.countCurrent}>{index + 1}</Text>
                    <Text style={styles.countTotal}>/{campaigns.length}</Text>
                    {campaigns.length === 1 ? ' active campaign' : ' active campaigns'}
                  </Text>

                  <View style={styles.listActions}>
                    <Pressable
                      onPress={reload}
                      hitSlop={Spacing.two}
                      accessibilityRole="button"
                      accessibilityLabel="Refresh"
                    >
                      <IconRefresh size={15} color={Colors.light.ink3} />
                    </Pressable>
                    <Arrow
                      direction="left"
                      disabled={index <= 0}
                      onPress={() => goTo(index - 1)}
                    />
                    <Arrow
                      direction="right"
                      disabled={index >= campaigns.length - 1}
                      onPress={() => goTo(index + 1)}
                    />
                  </View>
                </View>

                <ScrollView
                  ref={carousel}
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  // `snapToInterval` e não `pagingEnabled`: com o espaço entre
                  // cartões, a página do RN (a largura da viewport) e o passo
                  // real do carrossel deixam de coincidir, e a lista para
                  // desalinhada a partir do segundo cartão.
                  snapToInterval={step}
                  decelerationRate="fast"
                  contentContainerStyle={styles.carousel}
                  onMomentumScrollEnd={(event) =>
                    setScrolledTo(Math.round(event.nativeEvent.contentOffset.x / step))
                  }
                >
                  {campaigns.map((campaign) => (
                    <View key={campaign.id} style={{ width: cardWidth }}>
                      <CampaignCard campaign={campaign} hasSession={hasSession} />
                    </View>
                  ))}
                </ScrollView>

                {campaigns.length > 1 ? (
                  <View style={styles.dots}>
                    {campaigns.map((campaign, i) => (
                      <Pressable
                        key={campaign.id}
                        onPress={() => goTo(i)}
                        hitSlop={Spacing.two}
                        accessibilityRole="button"
                        accessibilityLabel={`Go to campaign ${i + 1}`}
                        style={[styles.dot, i === index && styles.dotActive]}
                      />
                    ))}
                  </View>
                ) : null}
              </>
            ) : null}
          </>
        ) : null}

        {tab === 'mine' ? (
          <EmptyState
            Icon={IconTarget}
            title="You haven't joined any campaign yet"
            text="Explore active campaigns and join to start earning."
          />
        ) : null}

        {tab === 'rewards' ? (
          <EmptyState
            Icon={IconBell}
            title="No rewards yet"
            text="Complete campaign tasks to receive USDC and $XLEE rewards here."
          />
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

/**
 * Estado da sessão no topo. O web pinta o modo convidado de âmbar; sem token
 * âmbar no design system, o convidado fica neutro — e neutro é honesto aqui,
 * já que não estar logado não é erro.
 */
function SessionBanner({ hasSession }: { hasSession: boolean }) {
  const router = useRouter();

  return (
    <View style={[styles.banner, hasSession ? styles.bannerActive : styles.bannerGuest]}>
      <View style={[styles.bannerIcon, hasSession ? styles.bannerIconActive : styles.bannerIconGuest]}>
        <IconClock size={15} color={hasSession ? Colors.light.success : Colors.light.ink2} />
      </View>

      <View style={styles.flex}>
        <Text style={styles.bannerTitle}>{hasSession ? 'Testnet Session Active' : 'Guest Mode'}</Text>
        <Text style={styles.bannerText}>
          {hasSession
            ? 'Ready to participate and collect rewards.'
            : 'Connect your wallet or authenticate via Chat.'}
        </Text>
      </View>

      {/* No web este botão é um Link para "/", a home do chat — é lá que a
          autenticação acontece. Mesma rota aqui. */}
      <Pressable
        onPress={() => router.navigate('/')}
        style={({ pressed }) => [styles.bannerButton, pressed && styles.pressed]}
        accessibilityRole="button"
      >
        <Text style={styles.bannerButtonText}>{hasSession ? 'Sync Wallet' : 'Login'}</Text>
      </Pressable>
    </View>
  );
}

function TabBar({
  tab,
  onChange,
  exploreCount,
  hasSession,
}: {
  tab: Tab;
  onChange: (next: Tab) => void;
  exploreCount: number;
  hasSession: boolean;
}) {
  const router = useRouter();

  // "My Campaigns" e "Rewards" contam a partir da sessão, que não existe
  // ainda — por isso zero fixo em vez de um número inventado.
  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'explore', label: 'Explore', count: exploreCount },
    { id: 'mine', label: 'My Campaigns', count: 0 },
    { id: 'rewards', label: 'Rewards', count: 0 },
  ];

  return (
    <View style={styles.tabBar}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.tabScroller}
      >
        {tabs.map(({ id, label, count }) => {
          const active = tab === id;
          return (
            <Pressable
              key={id}
              onPress={() => onChange(id)}
              style={[styles.tab, active && styles.tabActive]}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
            >
              <Text style={[styles.tabText, active && styles.tabTextActive]}>{label}</Text>
              {count > 0 ? (
                <View style={[styles.tabBadge, active && styles.tabBadgeActive]}>
                  <Text style={[styles.tabBadgeText, active && styles.tabBadgeTextActive]}>
                    {count}
                  </Text>
                </View>
              ) : null}
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Criar campanha exige sessão — a rota resolve o criador pelo Bearer.
          Sem sessão o botão leva ao chat, que é onde a autenticação acontece,
          igual ao "Login" do banner; com sessão, abre o formulário. */}
      <Pressable
        onPress={() => router.push(hasSession ? '/campaigns/new' : '/')}
        style={({ pressed }) => [styles.createButton, pressed && styles.pressed]}
        accessibilityRole="button"
        accessibilityLabel={hasSession ? 'Create campaign' : 'Sign in to create a campaign'}
      >
        <IconPlus size={16} sw={2.2} color={Colors.light.card} />
      </Pressable>
    </View>
  );
}

const HOW_STEPS = [
  'Join a campaign and complete the required steps.',
  'Verify your tasks to unlock the reward claim.',
  'Claim the reward using your Testnet session identity.',
  'Refresh to sync the latest campaign status.',
];

function HowItWorks({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <View style={styles.howBox}>
      <Pressable
        onPress={onToggle}
        style={({ pressed }) => [styles.howHeader, pressed && styles.pressed]}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
      >
        <IconTarget size={16} color={Colors.light.accent} />
        <Text style={styles.howTitle}>How it works — Testnet</Text>
        {/* A rotação vai no wrapper: `IconProps` não expõe `style`, e abrir
            esse contrato para um único uso espalharia estilo por todos os
            ícones do app. */}
        <View style={open ? styles.chevronOpen : undefined}>
          <IconChevronDown size={16} sw={2.2} color={Colors.light.ink3} />
        </View>
      </Pressable>

      {open ? (
        <View style={styles.howSteps}>
          {HOW_STEPS.map((step, i) => (
            <View key={step} style={styles.howStep}>
              <View style={styles.howNumber}>
                <Text style={styles.howNumberText}>{i + 1}</Text>
              </View>
              <Text style={styles.howStepText}>{step}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

/**
 * Esqueleto da primeira carga, na silhueta do resultado.
 *
 * O spinner centralizado que havia aqui ocupava uma fração da altura do
 * cartão de campanha, então a tela dava um salto grande no instante em que a
 * lista chegava — bem maior que o da Traction, porque o cartão é alto.
 *
 * As alturas são medidas contra o layout real: um esqueleto de altura errada
 * promete uma silhueta e entrega outra, e aí a tela pula do mesmo jeito.
 */
function CampaignsSkeleton() {
  return (
    <View style={styles.skeleton} accessible accessibilityLabel="Loading campaigns">
      <Skeleton height={16} width="55%" radius={Radius.sm} />
      <Skeleton height={470} radius={Radius.lg} />
      <Skeleton height={8} width={68} radius={Radius.pill} style={styles.skeletonDots} />
    </View>
  );
}

function Arrow({
  direction,
  disabled,
  onPress,
}: {
  direction: 'left' | 'right';
  disabled: boolean;
  onPress: () => void;
}) {
  const Icon = direction === 'left' ? IconChevronLeft : IconChevronRight;

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.arrow,
        disabled && styles.arrowDisabled,
        pressed && !disabled && styles.pressed,
      ]}
      accessibilityRole="button"
      accessibilityLabel={direction === 'left' ? 'Previous' : 'Next'}
      accessibilityState={{ disabled }}
    >
      <Icon size={15} sw={2.2} color={Colors.light.accent} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: {
    paddingHorizontal: H_PADDING,
    paddingTop: Spacing.four,
    gap: Spacing.three - 4,
  },
  pressed: { opacity: 0.7 },

  // ── Banner de sessão ───────────────────────────────────────────────────
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two + 2,
    padding: Spacing.three - 4,
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  bannerActive: {
    backgroundColor: Colors.light.successSoft,
    borderColor: Colors.light.successBorder,
  },
  bannerGuest: { backgroundColor: Colors.light.card, borderColor: Colors.light.border },
  bannerIcon: {
    width: 30,
    height: 30,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bannerIconActive: { backgroundColor: Colors.light.successBorder },
  bannerIconGuest: { backgroundColor: Colors.light.bg },
  bannerTitle: { fontFamily: Fonts.bold, fontSize: 13, color: Colors.light.ink },
  bannerText: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.ink2, marginTop: 1 },
  bannerButton: {
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two - 1,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.accent,
  },
  bannerButtonText: { fontFamily: Fonts.bold, fontSize: 12, color: Colors.light.card },

  // ── Abas ───────────────────────────────────────────────────────────────
  tabBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two - 2,
    padding: Spacing.one + 2,
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    ...CardShadow,
  },
  tabScroller: { alignItems: 'center', gap: Spacing.one },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two - 3,
    paddingHorizontal: Spacing.three - 3,
    paddingVertical: Spacing.two,
    borderRadius: Radius.md,
  },
  tabActive: { backgroundColor: Colors.light.accent },
  tabText: { fontFamily: Fonts.bold, fontSize: 13, color: Colors.light.ink3 },
  tabTextActive: { color: Colors.light.card },
  tabBadge: {
    paddingHorizontal: Spacing.two - 3,
    paddingVertical: 1,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accentSoft,
  },
  // Translúcido sobre o acento, como o `bg-white/25` do web.
  tabBadgeActive: { backgroundColor: 'rgba(255,255,255,0.28)' },
  tabBadgeText: { fontFamily: Fonts.bold, fontSize: 10, color: Colors.light.accent },
  tabBadgeTextActive: { color: Colors.light.card },
  createButton: {
    width: 34,
    height: 34,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accent,
  },
  createButtonDisabled: { opacity: 0.45 },

  // ── Como funciona ──────────────────────────────────────────────────────
  howBox: {
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    overflow: 'hidden',
    ...CardShadow,
  },
  howHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three - 4,
    paddingVertical: Spacing.two + 2,
  },
  howTitle: {
    flex: 1,
    fontFamily: Fonts.bold,
    fontSize: 11,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
  },
  chevronOpen: { transform: [{ rotate: '180deg' }] },
  howSteps: {
    gap: Spacing.two,
    paddingHorizontal: Spacing.three - 4,
    paddingBottom: Spacing.three - 4,
  },
  howStep: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.two },
  howNumber: {
    width: 18,
    height: 18,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  howNumberText: { fontFamily: Fonts.bold, fontSize: 10, color: Colors.light.accent },
  howStepText: { flex: 1, fontFamily: Fonts.sans, fontSize: 13, lineHeight: 19, color: Colors.light.ink2 },

  // ── Contador e navegação ───────────────────────────────────────────────
  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.one,
    marginTop: Spacing.two - 2,
  },
  count: {
    fontFamily: Fonts.bold,
    fontSize: 12,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: Colors.light.ink2,
  },
  countCurrent: { color: Colors.light.accent },
  countTotal: { color: Colors.light.ink3 },
  listActions: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  arrow: {
    width: 30,
    height: 30,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  arrowDisabled: { opacity: 0.4 },

  // ── Carrossel ──────────────────────────────────────────────────────────
  skeleton: { gap: Spacing.three - 4 },
  skeletonDots: { alignSelf: 'center' },
  carousel: { gap: CARD_GAP },
  dots: { flexDirection: 'row', justifyContent: 'center', gap: Spacing.two - 2 },
  dot: { width: 8, height: 8, borderRadius: Radius.pill, backgroundColor: Colors.light.border },
  dotActive: { width: 22, backgroundColor: Colors.light.accent },
});
