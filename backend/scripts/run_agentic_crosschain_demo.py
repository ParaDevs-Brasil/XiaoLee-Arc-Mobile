"""
run_agentic_crosschain_demo.py — Loop agêntico REAL com decisão de caminho cross-chain.

Prova o "Agentic 30%" na prática: uma campanha com creators em TRÊS chains (Arc, Solana
e Stellar); o ClaudeAgentEngine (Claude via API, não mock) descobre, avalia e DECIDE
sozinho qual trilho usar por creator — pay_creator_nanopayment (Arc direto) vs
payout_cross_chain_nanopayment (CCTP real Arc->Solana / Arc->Stellar via CctpForwarder
+ hook_data).

Reusa o código de produção (_run_agent_task de agent_routes.py) — não é uma simulação
paralela do loop.

Uso:
    cd backend && ../.venv/bin/python scripts/run_agentic_crosschain_demo.py           # cross-chain sandbox
    cd backend && ../.venv/bin/python scripts/run_agentic_crosschain_demo.py --live    # burn/mint REAL no CCTP

--live: só as pernas cross-chain (CCTP Arc->Solana/Stellar) ficam reais; o pagamento
Arc-direto fica em sandbox (ARC_SANDBOX=true forçado aqui) pra demo não depender do
estado do Circle W3S.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true", help="CCTP real (burn no Arc, mint na Solana)")
parser.add_argument("--budget", type=float, default=0.15)
parser.add_argument("--reward", type=float, default=0.05)
args = parser.parse_args()

# Flags ANTES de importar settings (dataclass frozen, lê env no import)
os.environ["SOLANA_CCTP_ENABLED"] = "true"
os.environ["STELLAR_CCTP_ENABLED"] = "true"
os.environ["BRIDGE_SANDBOX"] = "false" if args.live else "true"
os.environ["ARC_SANDBOX"] = "true"  # W3S fica sandbox — o live desta demo é o CCTP

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=False)
# override=False: as flags acima têm precedência sobre o .env
os.environ["SOLANA_CCTP_ENABLED"] = "true"
os.environ["STELLAR_CCTP_ENABLED"] = "true"
os.environ["BRIDGE_SANDBOX"] = "false" if args.live else "true"
os.environ["ARC_SANDBOX"] = "true"

from sqlalchemy import select

from database.database import create_tables, init_db
from database.models import Campaign, CampaignParticipant, User

# SessionLocal global só existe depois do init_db() (no server é o lifespan que chama)
_, SessionLocal = init_db()

CAMPAIGN_NAME = "Demo Cross-Chain Lepton"

# Creator Solana determinístico da demo (seed fixa — reproduzível entre runs)
def demo_solana_creator_pubkey() -> str:
    from solders.keypair import Keypair

    seed = b"xiaolee-demo-creator-solana-01".ljust(32, b"\x00")
    return str(Keypair.from_seed(seed).pubkey())


# Creator Stellar determinístico (mesma ideia — o payout live encaminha via CctpForwarder
# + hook_data, então a conta nem precisa existir on-chain pro burn sair)
def demo_stellar_creator_pubkey() -> str:
    from stellar_sdk import Keypair

    seed = b"xiaolee-demo-creator-stellar-1".ljust(32, b"\x00")
    return Keypair.from_raw_ed25519_seed(seed).public_key


async def seed() -> int:
    """Cria (idempotente) campanha + 3 creators: @demo_arc_creator, @demo_sol_creator
    e @demo_xlm_creator."""
    solana_wallet = demo_solana_creator_pubkey()
    stellar_wallet = demo_stellar_creator_pubkey()
    async with SessionLocal() as session:
        result = await session.execute(select(Campaign).where(Campaign.name == CAMPAIGN_NAME))
        campaign = result.scalars().first()
        if not campaign:
            campaign = Campaign(
                creator_twitter_user_id="demo_lepton",
                name=CAMPAIGN_NAME,
                description="Demo: agente decide o trilho de pagamento por creator (Arc vs CCTP cross-chain)",
                # sem campaign_type o GET /campaigns 500a (response model exige str)
                campaign_type="engagement",
                reward_token="USDC",
                reward_per_participant=0.05,
                max_participants=10,
                reward_pool=1.0,
                status="active",
            )
            session.add(campaign)
            await session.flush()

        async def ensure_creator(handle: str, chain: str, solana_wallet_val=None, stellar_wallet_val=None):
            r = await session.execute(select(User).where(User.twitter_handle == handle))
            user = r.scalars().first()
            if not user:
                user = User(twitter_handle=handle, twitter_user_id=f"uid_{handle}")
                session.add(user)
                await session.flush()
            r = await session.execute(
                select(CampaignParticipant).where(
                    CampaignParticipant.campaign_id == campaign.id,
                    CampaignParticipant.user_id == user.id,
                )
            )
            if not r.scalars().first():
                session.add(CampaignParticipant(
                    campaign_id=campaign.id,
                    user_id=user.id,
                    status="tasks_verified",
                    has_followed=True,
                    has_replied=True,
                    has_retweeted=True,
                    chain=chain,
                    solana_wallet=solana_wallet_val,
                    stellar_wallet=stellar_wallet_val,
                ))

        await ensure_creator("demo_arc_creator", "arc")
        await ensure_creator("demo_sol_creator", "solana", solana_wallet_val=solana_wallet)
        await ensure_creator("demo_xlm_creator", "stellar", stellar_wallet_val=stellar_wallet)
        await session.commit()
        print(f"campanha #{campaign.id} '{CAMPAIGN_NAME}' seedada")
        print(f"  @demo_arc_creator  chain=arc")
        print(f"  @demo_sol_creator  chain=solana wallet={solana_wallet}")
        print(f"  @demo_xlm_creator  chain=stellar wallet={stellar_wallet}")
        return campaign.id


async def main() -> None:
    from server.settings import settings

    print(f"modo: {'LIVE (CCTP real)' if args.live else 'SANDBOX'} | budget={args.budget} | reward={args.reward}")
    print(f"flags: bridge_sandbox={settings.bridge_sandbox} solana_cctp_enabled={settings.solana_cctp_enabled} arc_sandbox={settings.arc_sandbox}")
    assert settings.anthropic_api_key, "ANTHROPIC_API_KEY ausente"

    await create_tables()  # no-op quando o schema já existe (create_all é idempotente)
    campaign_id = await seed()

    from server.routes.agent_routes import _RUNS, _run_agent_task

    run_id = str(uuid.uuid4())
    _RUNS[run_id] = {
        "status": "pending", "campaign_id": campaign_id, "budget_usdc": args.budget,
        "steps": [], "payments": [], "total_paid_usdc": 0.0, "final_message": "", "error": None,
    }

    print(f"\nrodando ClaudeAgentEngine (modelo {settings.claude_model})...\n")
    await _run_agent_task(
        run_id=run_id,
        campaign_id=campaign_id,
        budget_usdc=args.budget,
        reward_per_creator=args.reward,
        db_session_factory=SessionLocal,
    )

    run = _RUNS[run_id]
    print(f"\n{'=' * 60}")
    print(f"status: {run['status']}")
    if run.get("error"):
        print(f"error: {run['error']}")
    print(f"steps: {len(run['steps'])}")
    for s in run["steps"]:
        tool = s["tool_name"]
        result_str = json.dumps(s["tool_result"], default=str)[:140]
        print(f"  [{s['step']}] {tool} -> {result_str}")
    print(f"\npagamentos ({len(run['payments'])}), total {run['total_paid_usdc']:.4f} USDC:")
    for p in run["payments"]:
        print(f"  {p['creator_id']}: {p['amount_usdc']} USDC | tx={p['tx']}")
    print(f"\nresumo do agente:\n{run['final_message']}")


if __name__ == "__main__":
    asyncio.run(main())
