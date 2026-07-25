from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import httpx

_PERSONA = (
    "You are XiaoLee, a kawaii, smart, and genuinely helpful AI assistant "
    "for the XiaoLee platform on Solana. "
    "Your personality is warm, cheerful, and degen-friendly — like a crypto-native friend who "
    "actually knows her stuff. Use kawaii emojis naturally (🌸, ✨, 💕, 🚀, 💜). "
    "Keep responses conversational and human — 2 to 4 sentences for simple questions, "
    "more when real detail is needed. Never use markdown formatting (no asterisks, no bold). "
    "CRITICAL RULE: reply in the EXACT same language the user writes in. "
    "Portuguese in → Portuguese out. English in → English out. Never switch languages."
)

# Intent classification: always the fast flash model.
# gemini-flash-latest resolves to the latest Gemini Flash (currently gemini-3-flash-preview).
# Not a thinking model → deterministic JSON, sub-second latency.
_INTENT_MODEL = "gemini-flash-latest"

# Reply fallback: same fast model — always available, Gemini 3 Flash quality.
_REPLY_FALLBACK = "gemini-flash-latest"


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        # model = the premium model configured via GEMINI_MODEL env var
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _api_url(self, model: str) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.api_key}"
        )

    _ERROR_PHRASES = frozenset([
        "No momento não consegui gerar resposta.",
        "Não consegui responder agora. Tenta de novo em um instante!",
        "Posso ajudar com saldo, cotação de swap e operações na Solana Devnet.",
    ])

    def _build_contents(self, user_text: str, history: list | None) -> List[Dict]:
        """Convert DB history (role: user/bot) to Gemini multi-turn contents array."""
        contents = []
        if history:
            for turn in history:
                role = turn.get("role", "")
                content = turn.get("content", "")
                if not content:
                    continue
                clean = re.sub(r"\[System Note:[^\]]+\]\s*", "", content).strip()
                if not clean:
                    continue
                # Skip error/fallback messages — they confuse the model.
                if any(phrase in clean for phrase in self._ERROR_PHRASES):
                    continue
                gemini_role = "model" if role == "bot" else "user"
                contents.append({"role": gemini_role, "parts": [{"text": clean}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})
        return contents

    async def _call(self, payload: Dict, model: str, timeout: float = 25) -> Dict:
        """Single HTTP call to a given Gemini model."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self._api_url(model), json=payload)
            resp.raise_for_status()
            return resp.json()

    async def _call_with_fallback(self, payload: Dict) -> Dict:
        """Try the premium model (short timeout); on any failure use the fallback."""
        if self.model != _REPLY_FALLBACK:
            try:
                body = await self._call(payload, self.model, timeout=10)
                # Confirm response has actual content (thinking models can exhaust token budget)
                parts = (
                    body.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts")
                )
                if parts:
                    return body
                print(f"[GeminiClient] {self.model} returned empty parts — falling back to {_REPLY_FALLBACK}")
            except Exception as e:
                print(f"[GeminiClient] {self.model} failed ({type(e).__name__}) — falling back to {_REPLY_FALLBACK}")

        return await self._call(payload, _REPLY_FALLBACK, timeout=25)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def classify_intent(self, user_text: str, history: list = None) -> Dict[str, Any]:
        """Always uses the fast, non-thinking model for deterministic JSON output."""
        if not self.enabled:
            return {"action": "fallback", "confidence": 0.0, "entities": {}}

        clean = re.sub(r"\[System Note:[^\]]+\]\s*", "", user_text).strip()

        prompt = (
            "Classify the user's intent. Return ONLY valid JSON: "
            '{"action": "check_balance|swap_quote|swap_execute|campaign_info|greeting|help'
            '|run_campaign_agent|pay_creator|discover_creators|check_budget", '
            '"confidence": 0.0, "entities": {}}. '
            "Context: XiaoLee is an agentic DeFi app on Arc (Circle, USDC). "
            "run_campaign_agent = user wants the autonomous agent to run/execute a campaign; "
            "pay_creator = pay a creator in USDC (Arc/Circle nanopayment, cross-chain/CCTP); "
            "discover_creators = find/list eligible creators; "
            "check_budget = campaign USDC budget/treasury questions. "
            "Use confidence >= 0.8 only when intent is crystal clear. "
            "User message: " + clean
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }

        try:
            body = await self._call(payload, _INTENT_MODEL, timeout=10)
        except Exception as e:
            print(f"Gemini classify_intent error: {e}")
            return {"action": "fallback", "confidence": 0.0, "entities": {}}

        text = (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )

        try:
            parsed = json.loads(text)
        except Exception:
            return {"action": "fallback", "confidence": 0.0, "entities": {}}

        return {
            "action": parsed.get("action", "fallback"),
            "confidence": float(parsed.get("confidence", 0.0)),
            "entities": parsed.get("entities", {}),
        }

    async def generate_reply(
        self,
        instruction: str,
        user_text: str,
        history: list = None,
    ) -> str:
        """Generates the actual XiaoLee response using the best available model."""
        if not self.enabled:
            return "Posso ajudar com saldo, cotação de swap e operações na Solana Devnet."

        system_text = _PERSONA + "\n\n" + instruction
        contents = self._build_contents(user_text, history)

        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            },
        }

        try:
            body = await self._call_with_fallback(payload)
        except Exception as e:
            print(f"Gemini generate_reply error: {e}")
            return "Não consegui responder agora. Tenta de novo em um instante! 🌸"

        return (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "No momento não consegui gerar resposta.")
        )
