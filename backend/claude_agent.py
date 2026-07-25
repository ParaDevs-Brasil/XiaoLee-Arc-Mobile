"""
claude_agent.py — ClaudeAgentEngine

Motor do loop agêntico nativo Anthropic:
    chama modelo → executa tool → devolve resultado → repete

Regra de ouro: wallet/budget NUNCA são parâmetros do modelo —
sempre injetados pelo executor via `context`.

Uso:
    engine = ClaudeAgentEngine(tools=CREATOR_PAY_TOOLS, executors=executors, max_steps=50)
    result = await engine.run(prompt, context={"campaign_id": 1, "budget": 100.0})
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

import anthropic

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class AgentStep:
    step: int
    tool_name: str
    tool_input: dict
    tool_result: dict


@dataclass
class AgentResult:
    run_id: str
    status: str  # completed | max_steps | budget_exhausted | failed
    steps: list[AgentStep] = field(default_factory=list)
    payments: list[dict] = field(default_factory=list)
    final_message: str = ""
    total_paid_usdc: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "steps": [
                {
                    "step": s.step,
                    "tool_name": s.tool_name,
                    "tool_input": s.tool_input,
                    "tool_result": s.tool_result,
                }
                for s in self.steps
            ],
            "payments": self.payments,
            "final_message": self.final_message,
            "total_paid_usdc": self.total_paid_usdc,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

ToolExecutor = Callable[[dict, dict], Coroutine[Any, Any, dict]]


class ClaudeAgentEngine:
    """
    Loop nativo Anthropic: chama modelo → executa tool → devolve resultado → repete.

    Args:
        tools:      Lista de tools em formato OpenAI (convertidas internamente).
        executors:  Dict {tool_name: async_callable(inputs, context) -> dict}.
        max_steps:  Trava de segurança absoluta (padrão: 50).
        model:      ID do modelo Claude (padrão: claude-sonnet-4-6).
        api_key:    ANTHROPIC_API_KEY (lido de env se não fornecido).
    """

    def __init__(
        self,
        tools: list[dict],
        executors: dict[str, ToolExecutor],
        max_steps: int = 50,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.anthropic_tools = self._convert_tools(tools)
        self.executors = executors
        self.max_steps = max_steps

    # ------------------------------------------------------------------
    # Tool format conversion — OpenAI → Anthropic
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_tools(openai_tools: list[dict]) -> list[dict]:
        """Convert OpenAI function tool format to Anthropic tool format."""
        result = []
        for t in openai_tools:
            func = t.get("function", t)
            result.append(
                {
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                }
            )
        return result

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, prompt: str, context: dict) -> AgentResult:
        """
        Executa o loop até finish_reason == 'end_turn' ou max_steps atingido.

        `context` é injetado em cada executor — nunca vai para o modelo.
        """
        run_id = str(uuid.uuid4())
        messages: list[dict] = [{"role": "user", "content": prompt}]
        steps: list[AgentStep] = []
        payments: list[dict] = []
        step_count = 0

        LOG.info("[agent] run_id=%s model=%s max_steps=%d", run_id, self.model, self.max_steps)

        while step_count < self.max_steps:
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    tools=self.anthropic_tools,
                    messages=messages,
                )
            except anthropic.APIError as exc:
                LOG.error("[agent] API error: %s", exc)
                return AgentResult(
                    run_id=run_id,
                    status="failed",
                    steps=steps,
                    payments=payments,
                    error=str(exc),
                )

            LOG.info(
                "[agent] step=%d stop_reason=%s content_blocks=%d",
                step_count,
                response.stop_reason,
                len(response.content),
            )

            # Model decided to stop
            if response.stop_reason == "end_turn":
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                total_paid = sum(p.get("amount_usdc", 0.0) for p in payments)
                LOG.info(
                    "[agent] completed run_id=%s steps=%d payments=%d total_usdc=%.4f",
                    run_id,
                    step_count,
                    len(payments),
                    total_paid,
                )
                return AgentResult(
                    run_id=run_id,
                    status="completed",
                    steps=steps,
                    payments=payments,
                    final_message=final_text,
                    total_paid_usdc=total_paid,
                )

            if response.stop_reason != "tool_use":
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                return AgentResult(
                    run_id=run_id,
                    status="completed",
                    steps=steps,
                    payments=payments,
                    final_message=final_text,
                    total_paid_usdc=sum(p.get("amount_usdc", 0.0) for p in payments),
                )

            # Collect tool calls from this response
            tool_results: list[dict] = []
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            async def _execute(tool_name: str, tool_input: dict) -> dict:
                executor = self.executors.get(tool_name)
                if not executor:
                    return {"error": f"Unknown tool: {tool_name}"}
                try:
                    return await executor(tool_input, context)
                except Exception as exc:
                    LOG.exception("[agent] executor %s raised: %s", tool_name, exc)
                    return {"error": str(exc), "tool": tool_name}

            # Tool calls do MESMO turno rodam em paralelo — o modelo já as emitiu como
            # independentes, e payouts CCTP levam minutos cada (attestation da Circle):
            # 2 payouts concorrentes ≈ latência de 1. Seguro porque os executores de
            # pagamento RESERVAM orçamento atomicamente antes do rail (creator_pay_tools/
            # cctp_tools) — sem isso, dois payouts passariam no check com o mesmo saldo.
            results = await asyncio.gather(
                *(_execute(b.name, dict(b.input)) for b in tool_blocks)
            )

            for block, tool_result in zip(tool_blocks, results):
                step_count += 1
                tool_name = block.name
                tool_input = dict(block.input)

                LOG.info(
                    "[agent] step=%d tool=%s input=%s result=%s",
                    step_count,
                    tool_name,
                    json.dumps(tool_input)[:200],
                    json.dumps(tool_result)[:300],
                )

                # Track payments for the summary
                if tool_name in ("pay_creator_nanopayment", "payout_cross_chain_nanopayment") and "tx" in tool_result:
                    payments.append(
                        {
                            "creator_id": tool_input.get("to"),
                            "amount_usdc": tool_input.get("amount_usdc"),
                            "tx": tool_result.get("tx"),
                            "intent_id": tool_input.get("intent_id"),
                            "step": step_count,
                        }
                    )

                steps.append(
                    AgentStep(
                        step=step_count,
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_result=tool_result,
                    )
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result),
                    }
                )

                # Budget exhausted — signal stop via context flag so next
                # check_budget call returns can_pay=false and model stops.
                if tool_result.get("budget_exhausted"):
                    context["_budget_exhausted"] = True

            # Append assistant turn + tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # max_steps reached
        LOG.warning("[agent] max_steps=%d reached for run_id=%s", self.max_steps, run_id)
        total_paid = sum(p.get("amount_usdc", 0.0) for p in payments)
        return AgentResult(
            run_id=run_id,
            status="max_steps",
            steps=steps,
            payments=payments,
            final_message=f"Agent reached max_steps limit ({self.max_steps}). Partial result.",
            total_paid_usdc=total_paid,
        )
