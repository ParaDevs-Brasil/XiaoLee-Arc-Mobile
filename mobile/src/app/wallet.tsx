import { useRouter } from 'expo-router';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { listMyCampaigns, type UserCampaignParticipation } from '@/api/backend';
import { EmptyState, ErrorState, Skeleton } from '@/components/feedback';
import { IconCheck, IconClock, IconGift, IconTarget, IconUser, IconWallet } from '@/components/icons';
import { PageHeading, ScreenShell } from '@/components/screen-shell';
import { SectionCard } from '@/components/section-card';
import { MiniStat, StatCard } from '@/components/stat-card';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { useBackendData } from '@/hooks/use-backend-data';
import { useSession } from '@/hooks/use-session';
import { formatTokenAmount, formatUSDC } from '@/lib/format';
import { getSession } from '@/lib/session';

/**
 * Tela de Wallet — destino da primeira linha do `ProfileMenu`, que até aqui não
 * levava a lugar nenhum.
 *
 * Porta `frontend/src/components/navbar/Wallet.tsx`, mas **não pela fonte de
 * dados dele**, e essa é a diferença que vale declarar.
 *
 * O painel do web mostra duas coisas: o saldo USDC on-chain de uma carteira
 * conectada (`GET /v1/arc/balance/{address}`) e uma lista de tokens vinda de
 * `UserData.balances`. Nenhuma das duas existe aqui:
 *
 *  1. Não há endereço. O web conecta por extensão de navegador (EIP-6963,
 *     Freighter); no mobile isso exigiria WalletConnect, que não está nas
 *     dependências. Sem endereço, aquela rota não tem o que consultar.
 *  2. `balances` vem do dossiê de `GET /user/{id}`, que o backend devolve como
 *     lista vazia literal (`campaigns_routes.py:555`) — junto com `swaps`,
 *     `transactions` e `chat_history`. Portar aquilo renderizaria vazio para
 *     sempre.
 *
 * O que o usuário realmente tem no XiaoLee hoje são as recompensas das
 * campanhas, e essas são reais: `GET /campaigns/me` devolve token, valor por
 * participante e o estado de cada participação. É daí que esta tela vive.
 *
 * O total é por token, nunca somado entre tokens. O web soma `valueUSD`, um
 * campo que o backend nunca preenche — somar USDC com $XLEE precisaria de preço,
 * e não há cotação para token de campanha.
 */

/** O trilho do produto é USDC (ver `ARC_LEPTON_ARCHITECTURE.md`); o resto é token de campanha. */
const USDC = 'USDC';

/** Em que ponto da jornada está a recompensa de uma participação. */
type Stage = 'claimed' | 'claimable' | 'pending';

/**
 * `tasks_claimed` é o único estado terminal; `tasks_verified` é o que libera o
 * resgate (ver `UserCampaignParticipation` em `api/backend.ts`). Qualquer outro
 * valor de `participation_status` ainda não rendeu nada.
 */
function stageOf(item: UserCampaignParticipation): Stage {
  if (item.tasks_claimed) return 'claimed';
  if (item.participation_status === 'tasks_verified') return 'claimable';
  return 'pending';
}

interface TokenTally {
  token: string;
  claimed: number;
  claimable: number;
  pending: number;
}

/** Uma linha por token, na ordem em que os tokens aparecem nas participações. */
function tallyByToken(campaigns: UserCampaignParticipation[]): TokenTally[] {
  const byToken = new Map<string, TokenTally>();

  for (const item of campaigns) {
    // O token vem de campo livre do formulário de criação, então "usdc" e
    // "USDC" são a mesma coisa e não podem virar duas linhas.
    const token = item.reward_token.trim().toUpperCase() || '—';
    const tally = byToken.get(token) ?? { token, claimed: 0, claimable: 0, pending: 0 };
    tally[stageOf(item)] += item.reward_per_participant;
    byToken.set(token, tally);
  }

  return [...byToken.values()];
}

/**
 * Sem sessão não há o que buscar: a rota resolve o participante pelo `Bearer` e
 * responderia 401. Lista vazia deixa a tela mostrar o estado de convidado, que
 * é o correto — não ter entrado ainda não é erro.
 */
async function fetchRewards(): Promise<UserCampaignParticipation[]> {
  const session = await getSession();
  if (!session) return [];
  return listMyCampaigns();
}

export default function WalletScreen() {
  // Barra de gestos do Android come o fim da lista sem este inset.
  const insets = useSafeAreaInsets();
  const { hasSession } = useSession();
  const { data, error, loading, refreshing, reload } = useBackendData(fetchRewards);

  const campaigns = data ?? [];
  const tallies = tallyByToken(campaigns);
  const usdc = tallies.find((item) => item.token === USDC);
  const otherTokens = tallies.filter((item) => item.token !== USDC);

  const counts = {
    claimed: campaigns.filter((item) => stageOf(item) === 'claimed').length,
    claimable: campaigns.filter((item) => stageOf(item) === 'claimable').length,
    pending: campaigns.filter((item) => stageOf(item) === 'pending').length,
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
          title="Wallet"
          subtitle="Rewards you have earned across XiaoLee campaigns."
        />

        {/* Aparece mesmo com dado na tela: uma recarga que falhou em silêncio
            faria saldos velhos passarem por atuais. */}
        {error && hasSession ? (
          <ErrorState title="Couldn't load your wallet" message={error} onRetry={reload} />
        ) : null}

        {loading && !data ? <WalletSkeleton /> : null}

        {data && !hasSession ? <GuestState /> : null}

        {data && hasSession ? (
          <>
            <StatCard
              size="lg"
              Icon={IconWallet}
              label="USDC claimed"
              value={`$${formatUSDC(usdc?.claimed ?? 0)}`}
              sub={heroSubLabel(usdc, otherTokens)}
            />

            <View style={styles.strip}>
              <MiniStat Icon={IconCheck} label="Claimed" value={String(counts.claimed)} />
              <MiniStat Icon={IconGift} label="Claimable" value={String(counts.claimable)} />
              <MiniStat Icon={IconClock} label="Pending" value={String(counts.pending)} />
            </View>

            <SectionCard
              title="Rewards by token"
              subtitle="Never summed across tokens — campaign tokens have no price"
            >
              {tallies.length === 0 ? (
                <EmptyState
                  Icon={IconTarget}
                  title="No rewards yet"
                  text="Join a campaign and complete its tasks to start earning."
                />
              ) : (
                tallies.map((tally) => <TokenRow key={tally.token} tally={tally} />)
              )}
            </SectionCard>

            <NoWalletNote />
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

/**
 * Linha de apoio do herói.
 *
 * O número grande é só o USDC resgatado, então esta linha carrega o que ele
 * deixou de fora: o que ainda dá para resgatar, e que existem outros tokens.
 * Sem isso, alguém com 500 $XLEE resgatados leria "$0.00" como "não ganhei
 * nada".
 */
function heroSubLabel(usdc: TokenTally | undefined, others: TokenTally[]): string {
  const parts: string[] = [];

  const claimable = usdc?.claimable ?? 0;
  if (claimable > 0) parts.push(`$${formatUSDC(claimable)} ready to claim`);

  if (others.length > 0) {
    parts.push(others.length === 1 ? '1 other token below' : `${others.length} other tokens below`);
  }

  return parts.length > 0 ? parts.join(' · ') : 'Settled on Arc Testnet';
}

function TokenRow({ tally }: { tally: TokenTally }) {
  const total = tally.claimed + tally.claimable + tally.pending;

  return (
    <View style={styles.tokenRow}>
      <View style={styles.tokenMark}>
        <Text style={styles.tokenMarkText}>{tally.token.slice(0, 4)}</Text>
      </View>

      <View style={styles.flex}>
        <Text style={styles.tokenName}>{tally.token}</Text>
        <Text style={styles.tokenBreakdown}>
          {formatTokenAmount(tally.claimed)} claimed
          {tally.claimable > 0 ? ` · ${formatTokenAmount(tally.claimable)} claimable` : ''}
          {tally.pending > 0 ? ` · ${formatTokenAmount(tally.pending)} pending` : ''}
        </Text>
      </View>

      {/* O valor à direita é o total prometido pelas campanhas, não o saldo —
          por isso o rótulo diz "earned" e não "balance". */}
      <View style={styles.tokenRight}>
        <Text style={styles.tokenTotal}>{formatTokenAmount(total)}</Text>
        <Text style={styles.tokenTotalLabel}>earned</Text>
      </View>
    </View>
  );
}

/**
 * O web tem uma carteira conectada e mostra o saldo on-chain dela. O mobile não
 * tem conector, e uma tela chamada "Wallet" que não diz isso deixa o usuário
 * procurando um botão de conectar que não existe.
 */
function NoWalletNote() {
  return (
    <SectionCard title="No wallet connected">
      <Text style={styles.noteText}>
        Rewards are tied to your Testnet session, not to a wallet on this device. Connecting one —
        Arc, Solana or Stellar — is available on the web app, and lands here once the mobile
        connector ships.
      </Text>
      <Text style={styles.footer}>Secured by XiaoLee · USDC · x402</Text>
    </SectionCard>
  );
}

/**
 * Estado de convidado. O destino é o chat, que é onde a autenticação acontece —
 * mesma escolha do banner da Campaigns e do vazio das Notifications.
 */
function GuestState() {
  const router = useRouter();

  return (
    <SectionCard title="Your rewards" subtitle="Tied to your Testnet session">
      <View style={styles.guest}>
        <View style={styles.guestIcon}>
          <IconUser size={22} color={Colors.light.ink3} />
        </View>
        <Text style={styles.guestTitle}>No session yet</Text>
        <Text style={styles.guestText}>
          Sign in from the chat to see the rewards you have earned from campaigns.
        </Text>
        <Pressable
          onPress={() => router.navigate('/')}
          style={({ pressed }) => [styles.guestButton, pressed && styles.pressed]}
          accessibilityRole="button"
        >
          <Text style={styles.guestButtonText}>Go to chat</Text>
        </Pressable>
      </View>
    </SectionCard>
  );
}

/**
 * Esqueleto da primeira carga. Alturas medidas contra o layout real — um
 * esqueleto de altura errada promete uma silhueta e entrega outra, e aí a tela
 * pula do mesmo jeito.
 */
function WalletSkeleton() {
  return (
    <View style={styles.skeleton} accessible accessibilityLabel="Loading wallet">
      <Skeleton height={152} radius={Radius.lg} />
      <View style={styles.strip}>
        <Skeleton height={92} radius={Radius.lg} style={styles.flex} />
        <Skeleton height={92} radius={Radius.lg} style={styles.flex} />
        <Skeleton height={92} radius={Radius.lg} style={styles.flex} />
      </View>
      <Skeleton height={168} radius={Radius.lg} />
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: {
    paddingHorizontal: Spacing.three - 4,
    paddingTop: Spacing.four,
    gap: Spacing.three - 4,
  },
  skeleton: { gap: Spacing.three - 4 },
  strip: { flexDirection: 'row', gap: Spacing.two + 2 },
  pressed: { opacity: 0.7 },

  // ── Linha de token ─────────────────────────────────────────────────────
  tokenRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two + 2,
    padding: Spacing.two + 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
  },
  tokenMark: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.accentSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  tokenMarkText: {
    fontFamily: Fonts.bold,
    fontSize: 9,
    letterSpacing: 0.4,
    color: Colors.light.accent,
  },
  tokenName: { fontFamily: Fonts.semibold, fontSize: 13, color: Colors.light.ink },
  tokenBreakdown: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 2 },
  tokenRight: { alignItems: 'flex-end' },
  tokenTotal: { fontFamily: Fonts.bold, fontSize: 14, color: Colors.light.ink },
  tokenTotalLabel: {
    fontFamily: Fonts.bold,
    fontSize: 8,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
    marginTop: 1,
  },

  // ── Aviso de carteira ──────────────────────────────────────────────────
  noteText: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 20, color: Colors.light.ink2 },
  footer: {
    fontFamily: Fonts.bold,
    fontSize: 9,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
    textAlign: 'center',
    paddingTop: Spacing.two,
    marginTop: Spacing.two - 2,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.light.border,
  },

  // ── Convidado ──────────────────────────────────────────────────────────
  guest: { alignItems: 'center', gap: Spacing.two, paddingVertical: Spacing.four },
  guestIcon: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.bg,
  },
  guestTitle: { fontFamily: Fonts.semibold, fontSize: 14, color: Colors.light.ink },
  guestText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    lineHeight: 20,
    color: Colors.light.ink2,
    textAlign: 'center',
  },
  guestButton: {
    marginTop: Spacing.one,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accent,
  },
  guestButtonText: { fontFamily: Fonts.bold, fontSize: 13, color: Colors.light.card },
});
