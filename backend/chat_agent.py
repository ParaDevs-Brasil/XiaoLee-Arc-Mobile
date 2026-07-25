"""
chat_agent.py — ChatAgentEngine: loop agêntico do CHAT (web /chat + DM).

Engine que torna a Xiao Lee *agêntica* na conversa em vez de um chatbot
single-shot: roda um loop multi-step (chama modelo → executa tool(s) → devolve o
resultado bruto → chama de novo) até o Claude parar de pedir tools, encadeando
operações e raciocinando sobre resultados reais na voz dela.

Ativa só quando ``LLM_PROVIDER=anthropic``; o caminho Gemini/OpenAI em
``response_generator`` continua intacto como fallback.

NOTA: é uma engine DISTINTA do ``claude_agent.ClaudeAgentEngine`` (loop de
pagamento de campanha do rail Arc). Interfaces diferentes de propósito:
    - ChatAgentEngine(client, model)         → run(*, system_prompt, message, tools, tool_executor, history)
    - ClaudeAgentEngine(tools, executors)    → run(prompt, context)  [rail]
"""
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Safety bound on the tool loop — caps how many model↔tool round trips a single
# user turn may trigger before we stop and return whatever text we have.
MAX_AGENTIC_STEPS = 8

# Async callback: (tool_name, tool_input) -> string result fed back to Claude.
ToolExecutor = Callable[[str, Dict[str, Any]], Awaitable[str]]


def openai_tools_to_anthropic(tools: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert OpenAI function-format tool schemas to Anthropic ``input_schema`` format.

    OpenAI:    {"type": "function", "function": {"name", "description", "parameters"}}
    Anthropic: {"name", "description", "input_schema"}
    """
    converted: List[Dict[str, Any]] = []
    for tool in tools or []:
        fn = tool.get("function", tool)
        name = fn.get("name")
        if not name:
            continue
        converted.append({
            "name": name,
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return converted


class ChatAgentEngine:
    """Runs the manual Anthropic tool-use loop for one user turn."""

    def __init__(self, client, model: str = DEFAULT_ANTHROPIC_MODEL, max_steps: int = MAX_AGENTIC_STEPS):
        # client is an anthropic.AsyncAnthropic instance (owned by LLMClient)
        self.client = client
        self.model = model
        self.max_steps = max_steps

    async def run(
        self,
        *,
        system_prompt: str,
        message: str,
        tools: Optional[List[Dict[str, Any]]],
        tool_executor: ToolExecutor,
        history: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Drive the loop until Claude stops calling tools, then return the final text.

        Returns ``{"text", "executed_tools", "stop_reason", "usage"}``.
        """
        anthropic_tools = openai_tools_to_anthropic(tools)

        # Stable prefix (system prompt + tool list) → mark for prompt caching.
        # Render order is tools → system → messages, so the per-request user
        # message stays after the cached prefix and never invalidates it.
        system_blocks = [{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]
        if anthropic_tools:
            anthropic_tools[-1] = {**anthropic_tools[-1], "cache_control": {"type": "ephemeral"}}

        messages: List[Dict[str, Any]] = list(history or [])
        messages.append({"role": "user", "content": message})

        executed_tools: List[Dict[str, Any]] = []
        final_text = ""
        response = None

        for step in range(self.max_steps):
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system_blocks,
                "messages": messages,
                # Adaptive thinking lets Claude decide how much to reason per
                # step — interleaved with tool calls in the agentic loop.
                "thinking": {"type": "adaptive"},
            }
            if anthropic_tools:
                kwargs["tools"] = anthropic_tools

            response = await self.client.messages.create(**kwargs)

            # Server-side pause (e.g. interleaved tool limit) — resend to resume.
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            # Capture any text the model produced this step.
            text_now = "".join(b.text for b in response.content if b.type == "text")
            if text_now:
                final_text = text_now

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_use_blocks:
                break

            # Preserve the full assistant turn (thinking + tool_use blocks) — the
            # API needs them to match the tool_result we send next.
            messages.append({"role": "assistant", "content": response.content})

            tool_results: List[Dict[str, Any]] = []
            for block in tool_use_blocks:
                tool_input = block.input or {}
                try:
                    result_str = await tool_executor(block.name, tool_input)
                    is_error = False
                except Exception as exc:  # tool failure is fed back, not fatal
                    logger.error(f"[ChatAgent] tool '{block.name}' failed: {exc}", exc_info=True)
                    result_str = f"Error executing {block.name}: {exc}"
                    is_error = True

                executed_tools.append({"name": block.name, "input": tool_input})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                    "is_error": is_error,
                })

            messages.append({"role": "user", "content": tool_results})
            logger.info(
                f"[ChatAgent] step {step + 1}: executed {[t['name'] for t in executed_tools[-len(tool_results):]]}"
            )
        else:
            logger.warning(f"[ChatAgent] hit MAX_AGENTIC_STEPS={self.max_steps} without end_turn")

        return {
            "text": final_text,
            "executed_tools": executed_tools,
            "stop_reason": getattr(response, "stop_reason", None),
            "usage": getattr(response, "usage", None),
        }
