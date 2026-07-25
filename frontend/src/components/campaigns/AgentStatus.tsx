"use client";
import React, { useState } from 'react';
import {
  useAgentStatus,
  AgentRunStatus,
  paymentRecipient,
  extractCrossChainPayouts,
} from '@/hooks/useAgentStatus';
import { detectChainFromTx, explorerTxUrl, CHAIN_LABEL, type Chain } from '@/lib/chains';

// ── Icons ──────────────────────────────────────────────────────────────────
const IconBot = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/>
    <path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>
  </svg>
);
const IconSpinner = () => (
  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="31.4" strokeDashoffset="10"/>
  </svg>
);
const IconCheck = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const IconX = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconCoin = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <circle cx="12" cy="12" r="10"/><path d="M12 8v8m-3-5h6"/>
  </svg>
);

// ── Status helpers ─────────────────────────────────────────────────────────
const STATUS_LABEL: Record<AgentRunStatus, string> = {
  idle: 'Parado',
  pending: 'Iniciando...',
  running: 'Executando',
  completed: 'Concluído',
  max_steps: 'Limite atingido',
  budget_exhausted: 'Budget esgotado',
  failed: 'Falha',
};

const STATUS_COLOR: Record<AgentRunStatus, string> = {
  idle: 'bg-gray-100 text-gray-500 border-gray-200',
  pending: 'bg-amber-50 text-amber-600 border-amber-200',
  running: 'bg-blue-50 text-blue-600 border-blue-200',
  completed: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  max_steps: 'bg-[var(--main-bg)] text-[var(--text-secondary)] border-[var(--border)]',
  budget_exhausted: 'bg-orange-50 text-orange-600 border-orange-200',
  failed: 'bg-red-50 text-red-600 border-red-200',
};

const isTerminal = (s: AgentRunStatus) =>
  ['completed', 'max_steps', 'budget_exhausted', 'failed'].includes(s);

// ── Props ──────────────────────────────────────────────────────────────────
interface AgentStatusProps {
  campaignId: number;
  campaignBudget: number;
  rewardPerCreator?: number;
  isCreator?: boolean;
}

// ── Component ──────────────────────────────────────────────────────────────
export default function AgentStatus({
  campaignId,
  campaignBudget,
  rewardPerCreator = 5.0,
  isCreator = false,
}: AgentStatusProps) {
  const { runId, status, data, isRunning, error, startAgent, reset } = useAgentStatus();
  const [expanded, setExpanded] = useState(false);

  if (!isCreator) return null;

  const handleStart = () => startAgent(campaignId, campaignBudget, rewardPerCreator);

  return (
    <div className="mt-3 rounded-xl border border-[var(--border)] bg-[var(--accent-soft)] p-3">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[var(--accent)]"><IconBot /></span>
          <span className="text-xs font-bold text-gray-700">Agente IA</span>
          <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${STATUS_COLOR[status]}`}>
            {(status === 'pending' || status === 'running') && <IconSpinner />}
            {status === 'completed' && <IconCheck />}
            {status === 'failed' && <IconX />}
            {STATUS_LABEL[status]}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {data && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-[10px] font-semibold text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors"
            >
              {expanded ? 'Ocultar' : 'Detalhes'}
            </button>
          )}
          {status === 'idle' || isTerminal(status) ? (
            <button
              onClick={isTerminal(status) ? () => { reset(); } : handleStart}
              disabled={isRunning}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 text-white text-[11px] font-bold transition-colors"
            >
              <IconBot />
              {status === 'idle' ? 'Executar Agente' : 'Executar Novamente'}
            </button>
          ) : isRunning ? (
            <span className="text-[10px] text-gray-400 font-medium">
              {data?.steps_count ?? 0} steps...
            </span>
          ) : null}
        </div>
      </div>

      {/* Running start button (when idle, before any run) */}
      {status === 'idle' && (
        <p className="text-[11px] text-gray-400 mt-2">
          O agente vai descobrir criadores inscritos, avaliar elegibilidade e pagar em USDC via Arc sandbox.
        </p>
      )}

      {/* Summary stats (after run started) */}
      {data && status !== 'idle' && (
        <div className="flex items-center gap-4 mt-2 pt-2 border-t border-[var(--border)]">
          <div className="flex items-center gap-1 text-[11px] text-gray-500">
            <IconCoin />
            <span className="font-bold text-gray-700">{data.total_paid_usdc.toFixed(2)} USDC</span>
            <span>pagos</span>
          </div>
          <div className="text-[11px] text-gray-500">
            <span className="font-bold text-gray-700">{data.payments_count}</span> criadores
          </div>
          <div className="text-[11px] text-gray-500">
            <span className="font-bold text-gray-700">{data.steps_count}</span> steps
          </div>
          {runId && (
            <span className="ml-auto text-[9px] text-gray-300 font-mono truncate max-w-[80px]" title={runId}>
              {runId.slice(0, 8)}…
            </span>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="mt-2 text-[11px] text-red-500 font-medium">{error}</p>
      )}

      {/* Final message */}
      {data?.final_message && isTerminal(status) && (
        <p className="mt-2 text-[11px] text-gray-500 italic line-clamp-3">{data.final_message}</p>
      )}

      {/* Expandable: steps + payments */}
      {expanded && data && (
        <div className="mt-3 pt-3 border-t border-[var(--border)] space-y-3">

          {/* Payments — valor real decidido pelo agente por criador (F1.2) */}
          {data.payments.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">Pagamentos</p>
              <div className="space-y-1">
                {data.payments.map((p, i) => {
                  const chain = (p.destination_chain as Chain | undefined) ?? detectChainFromTx(p.tx);
                  const txUrl = explorerTxUrl(p.tx, chain);
                  return (
                    <div key={i} className="flex items-center gap-2 text-[11px] bg-emerald-50 border border-emerald-100 rounded-lg px-2.5 py-1.5">
                      <IconCheck />
                      <span className="font-mono text-gray-600 truncate max-w-[100px]">
                        {paymentRecipient(p).slice(0, 10)}…
                      </span>
                      {chain && (
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full bg-white border border-emerald-200 text-emerald-600">
                          {CHAIN_LABEL[chain]}
                        </span>
                      )}
                      {txUrl && (
                        <a
                          href={txUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[9px] font-semibold text-[var(--accent)] hover:underline"
                          title={p.tx}
                        >
                          tx ↗
                        </a>
                      )}
                      <span
                        className="font-bold text-emerald-700 ml-auto"
                        title="Valor decidido pelo agente com base no score do criador"
                      >
                        {Number(p.amount_usdc).toFixed(2)} USDC
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Timeline cross-chain — burn no Arc → attestation → mint no destino (F1.1) */}
          {(() => {
            const payouts = extractCrossChainPayouts(data.steps);
            if (payouts.length === 0) return null;
            return (
              <div>
                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">
                  Payouts cross-chain (CCTP)
                </p>
                <div className="space-y-1.5">
                  {payouts.map((cp) => (
                    <div key={cp.step} className="rounded-lg border border-[var(--border)] bg-white px-2.5 py-2 text-[10px]">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[var(--accent)]">#{cp.step}</span>
                        <span className="font-mono text-gray-600 truncate max-w-[110px]">{cp.to?.slice(0, 12)}…</span>
                        <span className="font-bold uppercase text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
                          Arc → {CHAIN_LABEL[cp.destination_chain] ?? cp.destination_chain}
                        </span>
                        {cp.receipt_pqc && (
                          <span
                            className="text-[9px] font-semibold text-emerald-600"
                            title="Recibo pós-quântico ML-DSA-87 emitido para este pagamento"
                          >
                            🔐 PQC
                          </span>
                        )}
                        <span className="ml-auto font-bold text-gray-700">
                          {Number(cp.amount_usdc).toFixed(2)} USDC
                        </span>
                      </div>
                      {cp.error ? (
                        <p className="mt-1 text-red-500">{cp.error}</p>
                      ) : (
                        <div className="mt-1.5 flex items-center gap-1 text-gray-500">
                          <span className="px-1.5 py-0.5 rounded bg-emerald-50 border border-emerald-100 text-emerald-600">
                            burn + attest {cp.latency ? `${cp.latency.burn_attest_s}s` : "✓"}
                          </span>
                          <span className="text-gray-300">→</span>
                          <span className="px-1.5 py-0.5 rounded bg-emerald-50 border border-emerald-100 text-emerald-600">
                            mint {cp.latency ? `${cp.latency.mint_s}s` : "✓"}
                          </span>
                          <span className="text-gray-300">→</span>
                          {(() => {
                            const url = explorerTxUrl(cp.tx, cp.destination_chain);
                            return url ? (
                              <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[var(--accent)] hover:underline font-semibold"
                                title={cp.tx}
                              >
                                {cp.status}{cp.latency ? ` · ${cp.latency.total_s}s` : ""} ↗
                              </a>
                            ) : (
                              <span>{cp.status}</span>
                            );
                          })()}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Recent steps */}
          {data.steps.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1.5">Últimos steps</p>
              <div className="space-y-1 max-h-36 overflow-y-auto">
                {data.steps.slice(-6).map((s) => (
                  <div key={s.step} className="flex items-start gap-2 text-[10px] text-gray-500">
                    <span className="shrink-0 font-bold text-[var(--accent)]">#{s.step}</span>
                    <span className="font-mono text-gray-600">{s.tool_name}</span>
                    {'error' in s.tool_result && (
                      <span className="text-red-400 ml-auto truncate max-w-[100px]">{String(s.tool_result.error)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
