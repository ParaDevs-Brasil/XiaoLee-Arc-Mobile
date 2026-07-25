import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api/api';

export type AgentRunStatus = 'idle' | 'pending' | 'running' | 'completed' | 'max_steps' | 'budget_exhausted' | 'failed';

export interface AgentStep {
  step: number;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_result: Record<string, unknown>;
}

// O backend grava cada payment como {creator_id, amount_usdc, tx, intent_id, step};
// `to`/`destination_chain` chegam quando o backend normalizar (roadmap F1.1) —
// use `paymentRecipient()` para ler o destinatário de forma robusta.
export interface AgentPayment {
  step: number;
  to?: string;
  creator_id?: string;
  destination_chain?: string;
  amount_usdc: number;
  tx: string;
  intent_id: string;
}

export function paymentRecipient(p: AgentPayment): string {
  return p.to ?? p.creator_id ?? "";
}

// Resultado do tool payout_cross_chain_nanopayment (steps[].tool_result)
export interface CrossChainPayout {
  step: number;
  tx: string;
  to: string;
  amount_usdc: number;
  destination_chain: "solana" | "stellar";
  status: string;
  receipt_pqc?: string;
  latency?: { burn_attest_s: number; mint_s: number; total_s: number };
  error?: string;
}

/** Extrai payouts cross-chain (CCTP burn→attest→mint) dos steps do run. */
export function extractCrossChainPayouts(steps: AgentStep[]): CrossChainPayout[] {
  return steps
    .filter((s) => s.tool_name === "payout_cross_chain_nanopayment")
    .map((s) => ({ step: s.step, ...(s.tool_result as unknown as Omit<CrossChainPayout, "step">) }))
    .filter((p) => Boolean(p.tx) || Boolean(p.error));
}

export interface AgentStatusData {
  agent_run_id: string;
  campaign_id: number;
  status: AgentRunStatus;
  steps_count: number;
  payments_count: number;
  total_paid_usdc: number;
  payments: AgentPayment[];
  steps: AgentStep[];
  final_message: string;
  error?: string | null;
}

interface UseAgentStatusReturn {
  runId: string | null;
  status: AgentRunStatus;
  data: AgentStatusData | null;
  isRunning: boolean;
  error: string | null;
  startAgent: (campaignId: number, budgetUsdc: number, rewardPerCreator?: number) => Promise<void>;
  reset: () => void;
}

const TERMINAL_STATUSES: AgentRunStatus[] = ['completed', 'max_steps', 'budget_exhausted', 'failed'];
const POLL_INTERVAL_MS = 2500;

export function useAgentStatus(): UseAgentStatusReturn {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<AgentRunStatus>('idle');
  const [data, setData] = useState<AgentStatusData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollStatus = useCallback(async (id: string) => {
    try {
      const resp = await api.get<AgentStatusData>(`/v1/agent/run-campaign/${id}/status`);
      const d = resp.data;
      setData(d);
      setStatus(d.status);
      if (TERMINAL_STATUSES.includes(d.status)) {
        stopPolling();
        if (d.error) setError(d.error);
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })
        ?.response?.data?.detail ?? (err as { message?: string })?.message ?? 'Erro ao consultar status do agente';
      setError(msg);
      stopPolling();
      setStatus('failed');
    }
  }, [stopPolling]);

  const startAgent = useCallback(async (
    campaignId: number,
    budgetUsdc: number,
    rewardPerCreator: number = 5.0,
  ) => {
    setError(null);
    setData(null);
    setRunId(null);
    setStatus('pending');
    stopPolling();

    try {
      const resp = await api.post<{ agent_run_id: string }>('/v1/agent/run-campaign', {
        campaign_id: campaignId,
        budget_usdc: budgetUsdc,
        reward_per_creator_usdc: rewardPerCreator,
      });
      const id = resp.data.agent_run_id;
      setRunId(id);

      // Start polling
      pollRef.current = setInterval(() => pollStatus(id), POLL_INTERVAL_MS);
      // First poll immediately
      await pollStatus(id);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })
        ?.response?.data?.detail ?? (err as { message?: string })?.message ?? 'Erro ao iniciar agente';
      setError(msg);
      setStatus('failed');
    }
  }, [pollStatus, stopPolling]);

  const reset = useCallback(() => {
    stopPolling();
    setRunId(null);
    setStatus('idle');
    setData(null);
    setError(null);
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const isRunning = status === 'pending' || status === 'running';

  return { runId, status, data, isRunning, error, startAgent, reset };
}
