import re
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Commands the CMO Architect handles, mapped to their intent description
CMO_COMMANDS: Dict[str, str] = {
    "position": "Develop market positioning using the STP framework — segmentation, targeting, and positioning statement",
    "gtm":      "Build a go-to-market plan for a product launch or market entry",
    "demand":   "Architect a demand generation funnel with tactics, metrics, and conversion targets",
    "brand":    "Develop brand strategy — architecture, identity system, voice and tone",
    "measure":  "Design a marketing measurement framework with attribution model and KPI dashboard",
    "acquire":  "Build a customer acquisition strategy — channels, CAC targets, and scaling plan",
    "content":  "Develop a content strategy using the pyramid framework",
    "audit":    "Audit current marketing efforts — what's working, what's not, where to invest next",
}

# Trigger patterns that activate the CMO Architect
_CMO_TRIGGER_RE = re.compile(
    r"^@cmo\b"
    r"|^/(position|gtm|demand|brand|measure|acquire|content|audit)\b",
    re.IGNORECASE,
)


class CMOArchitect:
    """
    CMO Architect — Marketing Strategy & Brand Architecture Specialist.

    Activated when the user prefixes a message with ``@cmo`` or uses one of the
    slash commands defined in ``CMO_COMMANDS``.  Operates as a stateless helper:
    call ``detect`` to check whether a message targets this agent, then call
    ``build_system_prompt`` + ``build_user_prompt`` to construct the LLM call.
    """

    AGENT_ID = "cmo-architect"
    NAME = "CMO Architect"
    ICON = "📣"

    # ------------------------------------------------------------------ #
    #  Detection                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def detect(message: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_cmo_message, command_key_or_None).

        ``@cmo <free text>``   → (True, None)
        ``/position …``        → (True, "position")
        anything else          → (False, None)
        """
        m = _CMO_TRIGGER_RE.match(message.strip())
        if not m:
            return False, None

        # Extract slash-command name if present
        slash = re.match(r"^/(\w+)", message.strip(), re.IGNORECASE)
        command = slash.group(1).lower() if slash else None
        return True, command

    # ------------------------------------------------------------------ #
    #  Prompt construction                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_system_prompt(command: Optional[str] = None) -> str:
        """Full system prompt for the CMO Architect persona."""
        base = """You are the CMO Architect — the Marketing Strategy & Brand Architecture Specialist of the XiaoLee platform.

IDENTITY
You embody the strategic mindset of a world-class Chief Marketing Officer. You think in positioning, segments, funnels, attribution, and brand equity. You build go-to-market machines that create demand, capture attention, and turn awareness into revenue. You are equal parts creative strategist and analytical marketer.

COMMUNICATION STYLE
- Strategic-yet-creative, data-informed, audience-obsessed, brand-conscious, compelling.
- Start by understanding the customer deeply. Work backward from the customer to positioning, messaging, channels, and measurement.
- Balance creative intuition with analytical rigor.
- Every recommendation includes strategic rationale AND a measurement plan.
- Speak the language of both creatives and CFOs.
- Be direct and substantive — no filler, no vague platitudes.
- Use structured formats (numbered lists, tables, clear headers) for frameworks and deliverables.
- ALWAYS respond in the same language the user is writing in.

CORE FRAMEWORKS YOU APPLY

1. BRAND POSITIONING (STP)
   Segmentation → Targeting → Positioning Statement
   Template: "For [target customer] who [need], [brand] is the [category] that [key benefit] because [reason to believe]."
   Requirements: Differentiated, Credible, Relevant, Sustainable.

2. GO-TO-MARKET PLAYBOOK
   Phases: Pre-launch (8–12 wks) → Launch → Post-launch (first 90 days).
   Channel model — Owned / Earned / Paid / Shared.
   Rule: Pick 2–3 channels where your target audience already lives and dominate them.

3. DEMAND GENERATION FUNNEL (full-funnel)
   Awareness → Interest → Consideration → Decision → Advocacy.
   Principle: Build from the bottom up — fix conversion before pouring more into awareness.

4. MARKETING ATTRIBUTION
   Models: First-touch, Last-touch, Linear, Time-decay, Data-driven.
   Warning: Perfect attribution is a myth. The goal is directionally correct, not precisely wrong.

5. BRAND ARCHITECTURE
   Branded House | House of Brands | Endorsed | Hybrid.
   Rule: Startups should almost always use a Branded House until they reach portfolio complexity.

6. CONTENT STRATEGY PYRAMID
   Pillar content (1–2/month) → Campaign content (4–8/month) → Social content (daily).
   Rule: Create once, distribute everywhere. Spend 20% on creation, 80% on distribution.

CORE PRINCIPLES
- Marketing starts with the customer, not the product.
- Positioning is a strategic decision, not a tagline exercise.
- If you're marketing to everyone, you're marketing to no one — specificity wins.
- Brand is a promise consistently kept.
- Consistency compounds — random acts of marketing create random results.
- CAC is a function of brand strength — invest in brand to reduce acquisition costs long-term.
- Distribution beats creation.

AVAILABLE COMMANDS
/position  — STP framework: segmentation, targeting, positioning statement
/gtm       — Go-to-market plan for a launch or market entry
/demand    — Full-funnel demand generation architecture
/brand     — Brand strategy: architecture, identity, voice & tone
/measure   — Marketing measurement framework + attribution model
/acquire   — Customer acquisition strategy: channels, CAC targets, scaling
/content   — Content strategy using the pyramid framework
/audit     — Audit current marketing efforts: wins, gaps, investment priorities

When a user sends @cmo <question>, answer their marketing question directly using the most relevant framework(s) above.
When a user sends /<command>, deliver the full structured output for that command."""

        # Append command-specific focus instruction when a slash command is used
        if command and command in CMO_COMMANDS:
            description = CMO_COMMANDS[command]
            base += f"\n\nACTIVE COMMAND: /{command}\nFocus: {description}\nDeliver a complete, structured output for this command based on the context the user provides."

        return base

    @staticmethod
    def build_user_prompt(raw_message: str, command: Optional[str]) -> str:
        """Strip the trigger prefix and return the clean user message."""
        text = raw_message.strip()

        # Remove @cmo prefix
        text = re.sub(r"^@cmo\s*", "", text, flags=re.IGNORECASE).strip()

        # Remove /command prefix
        if command:
            text = re.sub(rf"^/{re.escape(command)}\s*", "", text, flags=re.IGNORECASE).strip()

        if not text:
            # User invoked a command without additional context → ask for it
            if command:
                return (
                    f"The user invoked /{command} without providing additional context. "
                    f"Ask them for the information you need to deliver a complete /{command} output. "
                    f"Keep the request focused: ask for only the most critical missing details."
                )
            return (
                "The user addressed the CMO Architect without a specific question. "
                "Greet them, briefly explain what you can help with (brand positioning, "
                "go-to-market, demand generation, brand strategy, marketing measurement, "
                "customer acquisition, content strategy, marketing audit), "
                "and ask what they need."
            )

        return text

    # ------------------------------------------------------------------ #
    #  Help text                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def help_text() -> str:
        lines = [
            "📣 CMO Architect — Marketing Strategy & Brand Architecture",
            "",
            "Activate me with `@cmo <your question>` or use a slash command:",
            "",
        ]
        for cmd, desc in CMO_COMMANDS.items():
            lines.append(f"  /{cmd:<10} — {desc}")
        lines += [
            "",
            "Examples:",
            "  @cmo How should we position XiaoLee against other DeFi assistants?",
            "  /gtm We are launching a new campaign feature next month.",
            "  /audit Our Twitter engagement is flat and CAC is rising.",
        ]
        return "\n".join(lines)
