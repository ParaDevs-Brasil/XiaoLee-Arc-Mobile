import { Fragment } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import type { Campaign } from '@/api/backend';
import { IconList } from '@/components/icons';
import { CardShadow, Colors, Fonts, Radius, Spacing } from '@/constants/theme';
import { formatDate, formatTokenAmount } from '@/lib/format';

/**
 * Cartão de campanha — porta de `frontend/src/components/campaigns/CampaignCard.tsx`.
 *
 * A ordem dos blocos é a do web: cabeçalho, descrição, números com barra de
 * progresso, recompensa, tarefas exigidas, os três botões e o rodapé.
 *
 * Os textos vêm de `frontend/src/locales/en.json` (chaves `campaign_card.*`),
 * copiados em vez de reescritos — o mobile ainda não tem i18n, e inventar
 * outra redação faria as duas plataformas dizerem coisas diferentes sobre a
 * mesma campanha.
 */

/**
 * Faixas da barra de vagas, iguais às do web (`CampaignCard.tsx:28`): verde
 * até 60%, âmbar entre 60 e 90, vermelho a partir de 90.
 *
 * O mobile ficou só com verde e vermelho porque o design system não tinha
 * âmbar na época. Tem desde `3f74248`, então as três faixas voltam — e a do
 * meio importa: "enchendo" e "praticamente sem vaga" são decisões diferentes
 * para quem está pensando em entrar.
 */
const FILLING_PCT = 60;
const NEARLY_FULL_PCT = 90;

interface CampaignCardProps {
  campaign: Campaign;
  /**
   * Entrar, verificar e resgatar dependem de sessão. Sem ela os três botões
   * ficam travados com o mesmo texto do web ("Waiting for Testnet Session"),
   * em vez de falharem no toque.
   */
  hasSession: boolean;
}

export function CampaignCard({ campaign, hasSession }: CampaignCardProps) {
  // `completed_participants` conta **todo mundo inscrito**, não quem concluiu:
  // o backend preenche esse campo com um `count` de `CampaignParticipant` sem
  // filtrar por status (`campaigns_routes.py::list_campaigns`). O rótulo segue
  // o do web, "Enrolled", que é o que o número realmente significa.
  const enrolled = campaign.completed_participants || 0;
  const spotsLeft = Math.max(0, campaign.max_participants - enrolled);
  const pct =
    campaign.max_participants > 0
      ? Math.min(100, Math.round((enrolled / campaign.max_participants) * 100))
      : 0;

  const hasTasks = Boolean(campaign.profile_to_follow || campaign.tweet_id_to_engage);

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.name}>{campaign.name}</Text>
        <View style={styles.typeChip}>
          <Text style={styles.typeText}>{campaign.campaign_type}</Text>
        </View>
      </View>

      <View style={styles.body}>
        <Text style={styles.description} numberOfLines={3}>
          {campaign.description}
        </Text>

        <View style={styles.statsBox}>
          <View style={styles.statsGrid}>
            <Stat label="Max." value={String(campaign.max_participants)} />
            <Stat
              label="Pool"
              value={`${formatTokenAmount(campaign.reward_pool)} ${campaign.reward_token}`}
            />
            <Stat label="Enrolled" value={String(enrolled)} />
            <Stat
              label="Spots"
              value={spotsLeft === 0 ? 'Sold out' : String(spotsLeft)}
              alert={spotsLeft === 0}
            />
          </View>

          <View style={styles.progressHeader}>
            <Text style={styles.progressLabel}>Spots filled</Text>
            <Text style={styles.progressPct}>{pct}%</Text>
          </View>
          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                { width: `${pct}%` },
                pct >= FILLING_PCT && styles.progressFillFilling,
                pct >= NEARLY_FULL_PCT && styles.progressFillFull,
              ]}
            />
          </View>
        </View>

        <View style={styles.rewardBox}>
          <Text style={styles.rewardLabel}>Reward per participant</Text>
          <View style={styles.rewardValue}>
            <Text style={styles.rewardAmount}>
              {formatTokenAmount(campaign.reward_per_participant)}
            </Text>
            <Text style={styles.rewardToken}>{campaign.reward_token}</Text>
          </View>
        </View>

        {hasTasks ? (
          <View style={styles.tasksBox}>
            <View style={styles.tasksHeader}>
              <IconList size={13} color={Colors.light.ink2} />
              <Text style={styles.tasksTitle}>Required tasks</Text>
            </View>

            {campaign.profile_to_follow ? (
              <Task
                label="Follow:"
                value={campaign.profile_to_follow}
                url={`https://x.com/${campaign.profile_to_follow.replace(/^@/, '')}`}
              />
            ) : null}
            {campaign.tweet_id_to_engage ? (
              <Task
                label="Engage:"
                value={campaign.tweet_id_to_engage}
                url={campaign.tweet_id_to_engage}
              />
            ) : null}
          </View>
        ) : null}

        <View style={styles.actions}>
          <StepRail />
          <Action
            label={hasSession ? 'Join' : 'Waiting for Testnet Session'}
            disabled={!hasSession}
          />
        </View>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>@{campaign.creator_twitter_user_id}</Text>
        <Text style={styles.footerText}>{formatDate(campaign.created_at)}</Text>
      </View>
    </View>
  );
}

function Stat({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, alert && styles.statValueAlert]} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

/** Tarefa exigida. Abre no navegador — o alvo é sempre um link do X. */
function Task({ label, value, url }: { label: string; value: string; url: string }) {
  return (
    <View style={styles.task}>
      <Text style={styles.taskLabel}>{label}</Text>
      <Pressable
        onPress={() => {
          // Sem `catch` o app cai se não houver navegador para o esquema —
          // uma tarefa que não abre não justifica derrubar a tela.
          Linking.openURL(url).catch(() => {});
        }}
        accessibilityRole="link"
        hitSlop={Spacing.two}
        style={styles.taskLinkWrap}
      >
        <Text style={styles.taskLink} numberOfLines={1}>
          {value}
        </Text>
      </Pressable>
    </View>
  );
}

/**
 * A jornada da campanha: entrar, verificar as tarefas, resgatar.
 *
 * No web isto são três botões, cada um guiado por estado de participação real
 * (`isEnrolled`, `isTasksVerified`, `isPaid`). O mobile não tem esse estado —
 * sem sessão não existe participação para consultar —, então lá os três
 * ficavam `disabled` fixo: ~142px no rodapé de todo cartão que nunca dispara
 * nada, num carrossel que já não conseguia mostrar um cartão inteiro.
 *
 * O trilho conta a mesma progressão em ~18px e deixa uma única ação viva. Os
 * passos voltam a ser botões quando houver estado de participação para guiá-los.
 */
const STEPS = ['Join', 'Verify', 'Claim'] as const;

function StepRail() {
  return (
    // `accessible` no contêiner: o leitor de tela anuncia a jornada como uma
    // frase, em vez de soletrar seis nós soltos ("1", "Join", "2"…).
    <View
      style={styles.rail}
      accessible
      accessibilityLabel="Join, then verify tasks, then claim the reward"
    >
      {STEPS.map((label, i) => (
        <Fragment key={label}>
          {i > 0 ? <View style={styles.railLine} /> : null}
          <View style={styles.railStep}>
            <View style={styles.railDot}>
              <Text style={styles.railDotText}>{i + 1}</Text>
            </View>
            <Text style={styles.railLabel}>{label}</Text>
          </View>
        </Fragment>
      ))}
    </View>
  );
}

/**
 * Ação primária do cartão. O web pinta o primário com um gradiente rosa→roxo;
 * aqui ele é o acento chapado — o mobile não tem `expo-linear-gradient`, e o
 * design system define o primário como cor sólida.
 */
function Action({
  label,
  disabled,
  onPress,
}: {
  label: string;
  disabled?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.action,
        disabled && styles.actionDisabled,
        pressed && !disabled && styles.pressed,
      ]}
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(disabled) }}
    >
      <Text style={styles.actionText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: Radius.lg,
    backgroundColor: Colors.light.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
    overflow: 'hidden',
    ...CardShadow,
  },

  // ── Cabeçalho ──────────────────────────────────────────────────────────
  header: {
    gap: Spacing.two - 2,
    alignItems: 'flex-start',
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.light.border,
  },
  name: { fontFamily: Fonts.bold, fontSize: 15, lineHeight: 21, color: Colors.light.ink },
  typeChip: {
    paddingHorizontal: Spacing.two + 2,
    paddingVertical: 2,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.accentSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  typeText: {
    fontFamily: Fonts.bold,
    fontSize: 9,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.accent,
  },

  body: { padding: Spacing.three - 2, gap: Spacing.two + 2 },
  description: { fontFamily: Fonts.sans, fontSize: 13, lineHeight: 20, color: Colors.light.ink2 },

  // ── Números e progresso ────────────────────────────────────────────────
  statsBox: {
    gap: Spacing.two,
    padding: Spacing.two + 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  // Duas colunas com `wrap`: os quatro números viram 2x2 sem grid.
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: Spacing.two - 2 },
  stat: {
    width: '50%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingRight: Spacing.two,
  },
  statLabel: { fontFamily: Fonts.medium, fontSize: 12, color: Colors.light.ink3 },
  statValue: { fontFamily: Fonts.bold, fontSize: 12, color: Colors.light.ink, flexShrink: 1 },
  statValueAlert: { color: Colors.light.danger },

  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Spacing.two - 2,
  },
  progressLabel: { fontFamily: Fonts.medium, fontSize: 11, color: Colors.light.ink3 },
  progressPct: { fontFamily: Fonts.bold, fontSize: 11, color: Colors.light.ink2 },
  progressTrack: {
    height: 6,
    borderRadius: Radius.pill,
    backgroundColor: Colors.light.border,
    overflow: 'hidden',
  },
  progressFill: { height: '100%', borderRadius: Radius.pill, backgroundColor: Colors.light.success },
  progressFillFilling: { backgroundColor: Colors.light.warn },
  progressFillFull: { backgroundColor: Colors.light.danger },

  // ── Recompensa ─────────────────────────────────────────────────────────
  rewardBox: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.two,
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two + 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.accentSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  rewardLabel: { flex: 1, fontFamily: Fonts.semibold, fontSize: 12, color: Colors.light.ink2 },
  rewardValue: { flexDirection: 'row', alignItems: 'baseline', gap: Spacing.two - 2 },
  rewardAmount: { fontFamily: Fonts.bold, fontSize: 18, color: Colors.light.accent },
  rewardToken: { fontFamily: Fonts.bold, fontSize: 12, color: Colors.light.accent },

  // ── Tarefas ────────────────────────────────────────────────────────────
  tasksBox: {
    gap: Spacing.two - 2,
    padding: Spacing.two + 2,
    borderRadius: Radius.md,
    backgroundColor: Colors.light.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  tasksHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 2 },
  tasksTitle: {
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    color: Colors.light.ink2,
  },
  task: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 2 },
  taskLabel: { fontFamily: Fonts.sans, fontSize: 12, color: Colors.light.ink2 },
  taskLinkWrap: { flex: 1 },
  taskLink: {
    fontFamily: Fonts.medium,
    fontSize: 12,
    color: Colors.light.accent,
    textDecorationLine: 'underline',
  },

  // ── Ações ──────────────────────────────────────────────────────────────
  actions: { gap: Spacing.two + 2 },
  rail: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 2 },
  railStep: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two - 3 },
  // `flex: 1` no conector: são as linhas que absorvem a sobra, então os três
  // passos ficam distribuídos sem conta de largura.
  railLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: Colors.light.border },
  railDot: {
    width: 18,
    height: 18,
    borderRadius: Radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.light.bg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.light.border,
  },
  railDotText: { fontFamily: Fonts.bold, fontSize: 9, color: Colors.light.ink3 },
  railLabel: {
    fontFamily: Fonts.bold,
    fontSize: 10,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    color: Colors.light.ink3,
  },
  action: {
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: Radius.md,
    backgroundColor: Colors.light.accent,
  },
  actionDisabled: { opacity: 0.45 },
  actionText: { fontFamily: Fonts.semibold, fontSize: 13, color: Colors.light.card },
  pressed: { opacity: 0.7 },

  // ── Rodapé ─────────────────────────────────────────────────────────────
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.three - 2,
    paddingVertical: Spacing.two + 2,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.light.border,
  },
  footerText: { fontFamily: Fonts.sans, fontSize: 11, color: Colors.light.ink3 },
});
