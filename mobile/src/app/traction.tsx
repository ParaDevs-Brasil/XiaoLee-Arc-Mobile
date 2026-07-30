import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { getTractionStats, type PaymentEvent } from '@/api/backend';
import { EmptyState, ErrorState, LoadingState } from '@/components/feedback';
import { IconActivity, IconDollar, IconInbox, IconUser, IconUsers, IconZap } from '@/components/icons';
import { PageHeading, ScreenShell } from '@/components/screen-shell';
import { SectionCard } from '@/components/section-card';
import { StatCard } from '@/components/stat-card';
import { Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { useBackendData } from '@/hooks/use-backend-data';
import { formatUSDC, shortHash, timeAgo } from '@/lib/format';

/**
 * Tela de Traction — o painel público de USDC liquidado pelo agente na Arc.
 *
 * Porta `frontend/src/app/traction/page.tsx` para o vocabulário do mobile. A
 * rota (`GET /v1/traction/stats`) é pública: não exige sessão, então esta é a
 * única tela do app que mostra dado real sem login — de propósito, é a que o
 * júri do hackathon abre.
 */

/** Acima disto a liquidação deixa de parecer instantânea — mesmo corte do web. */
const LATENCY_OK_MS = 500;

export default function TractionScreen() {
  // Barra de gestos do Android come o fim da lista sem este inset.
  const insets = useSafeAreaInsets();
  // `getTractionStats` é função de módulo, então a identidade é estável e o
  // hook não recarrega a cada render.
  const { data, error, loading, refreshing, reload } = useBackendData(getTractionStats);

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
          title="Traction"
          subtitle="USDC the agent has settled on Arc — pull to refresh."
        />

        {/* Aparece mesmo com dado na tela: uma recarga que falhou em silêncio
            faria o usuário ler números velhos como se fossem atuais. */}
        {error ? (
          <ErrorState title="Couldn't load traction" message={error} onRetry={reload} />
        ) : null}

        {loading && !data ? <LoadingState label="Reading the payment rail…" /> : null}

        {data ? (
          <>
            <View style={styles.stats}>
              <StatCard
                Icon={IconDollar}
                label="USDC settled"
                value={`$${formatUSDC(data.total_usdc)}`}
                tone="success"
              />
              <StatCard
                Icon={IconActivity}
                label="Payments"
                value={String(data.total_payments)}
              />
              <StatCard
                Icon={IconUsers}
                label="Active creators"
                value={String(data.active_creators)}
              />
              <StatCard
                Icon={IconUser}
                label="Registered"
                value={String(data.registered_creators)}
                tone="neutral"
              />
            </View>

            <LatencyBar avg={data.avg_latency_ms} p95={data.p95_latency_ms} />

            <SectionCard title="Payment feed" subtitle="Latest settlements, newest first">
              {data.feed.length === 0 ? (
                <EmptyState
                  Icon={IconInbox}
                  title="No payments yet"
                  text="When the agent settles a nanopayment, it lands here."
                />
              ) : (
                data.feed.map((event) => <FeedRow key={event.intent_id} event={event} />)
              )}
            </SectionCard>
          </>
        ) : null}
      </ScrollView>
    </ScreenShell>
  );
}

/**
 * Saúde da liquidação em uma linha.
 *
 * O web pinta o estado degradado de âmbar, mas o design system só tem
 * `success` e `danger` — inventar um hex aqui violaria a regra de referenciar
 * sempre os tokens, então degradado usa `danger`.
 */
function LatencyBar({ avg, p95 }: { avg: number; p95: number }) {
  const ok = avg < LATENCY_OK_MS;
  const color = ok ? Colors.light.success : Colors.light.danger;

  return (
    <View style={[styles.latency, ok ? styles.latencyOk : styles.latencyWarn]}>
      <View style={[styles.latencyIcon, ok ? styles.latencyIconOk : styles.latencyIconWarn]}>
        <IconZap size={18} color={color} />
      </View>

      <View style={styles.flex}>
        <Text style={[styles.latencyTitle, { color }]}>
          {ok ? 'Settlement is fast' : 'Settlement is degraded'} · {Math.round(avg)}ms avg
        </Text>
        <Text style={styles.latencySub}>
          {p95 > 0
            ? `P95 ${Math.round(p95)}ms · decision to on-chain settlement`
            : 'Decision to on-chain settlement'}
        </Text>
      </View>
    </View>
  );
}

function FeedRow({ event }: { event: PaymentEvent }) {
  return (
    <View style={styles.feedRow}>
      <View style={styles.feedIcon}>
        <IconDollar size={14} color={Colors.light.success} />
      </View>

      <View style={styles.flex}>
        <Text style={styles.feedCreator} numberOfLines={1}>
          {event.creator}
        </Text>
        <Text style={styles.feedTx} numberOfLines={1}>
          {shortHash(event.tx)}
        </Text>
      </View>

      <View style={styles.feedRight}>
        <Text style={styles.feedAmount}>+${formatUSDC(event.amount)}</Text>
        <Text style={styles.feedTime}>{timeAgo(event.ts)}</Text>
      </View>
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

  // ── Métricas ───────────────────────────────────────────────────────────
  // `wrap` com os cartões em `flex: 1` e `minWidth: 140` dá dois por linha sem
  // conta de largura, e cai para um só em aparelho estreito.
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two + 2 },

  // ── Barra de latência ──────────────────────────────────────────────────
  latency: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two + 2,
    padding: Spacing.three - 4,
    borderRadius: Radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  latencyOk: { backgroundColor: Colors.light.successSoft, borderColor: Colors.light.successBorder },
  latencyWarn: { backgroundColor: Colors.light.dangerSoft, borderColor: Colors.light.danger },
  latencyIcon: {
    width: 36,
    height: 36,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  latencyIconOk: { backgroundColor: Colors.light.successBorder },
  latencyIconWarn: { backgroundColor: Colors.light.card },
  latencyTitle: { fontFamily: Fonts.bold, fontSize: 13 },
  latencySub: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink2, marginTop: 1 },

  // ── Feed ───────────────────────────────────────────────────────────────
  feedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two + 2,
    paddingHorizontal: Spacing.two + 2,
    paddingVertical: Spacing.two + 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
  },
  feedIcon: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.successSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.successBorder,
  },
  feedCreator: { fontFamily: Fonts.semibold, fontSize: 13, color: Colors.light.ink },
  feedTx: { fontFamily: Fonts.mono, fontSize: 10, color: Colors.light.ink3, marginTop: 2 },
  feedRight: { alignItems: 'flex-end' },
  feedAmount: { fontFamily: Fonts.bold, fontSize: 13, color: Colors.light.success },
  feedTime: { fontFamily: Fonts.sans, fontSize: 10, color: Colors.light.ink3, marginTop: 2 },
});
