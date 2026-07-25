from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .models import CampaignParticipant, CctpTransfer, PaymentIntent, SettledPayment, User, DMLog


class DatabaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(self, platform: str, user_id: str) -> User:
        stmt = select(User).where(User.twitter_user_id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                twitter_user_id=user_id,
                twitter_handle=f"{platform}_{user_id}",
            )
            self.session.add(user)
            await self.session.flush()

        return user

    async def set_telegram_chat_id(self, user_id: int, chat_id: str | int) -> None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalars().first()
        if not user:
            return
        user.telegram_chat_id = str(chat_id)
        await self.session.flush()

    async def log_dm(
        self,
        user_id: int,
        platform: str,
        content: str,
        message_type: str = "user",
        error_message: str = None,
    ):
        dm_log = DMLog(
            user_id=user_id,
            platform=platform,
            content=content,
            message_type=message_type,
            error_occurred=bool(error_message),
            error_message=error_message,
        )
        self.session.add(dm_log)
        await self.session.flush()
        return dm_log

    async def get_user_history(self, user_id: int, limit: int = 5) -> list[dict]:
        stmt = (
            select(DMLog)
            .where(DMLog.user_id == user_id)
            .order_by(DMLog.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        logs = result.scalars().all()
        return [{"role": log.message_type, "content": log.content} for log in reversed(logs)]

    # ------------------------------------------------------------------
    # Campaign participants — used by the agent tools
    # ------------------------------------------------------------------

    async def get_campaign_participants(
        self, campaign_id: int, limit: int = 50
    ) -> list[dict]:
        """Return enrolled/verified participants joined with user twitter_handle."""
        stmt = (
            select(CampaignParticipant, User)
            .join(User, User.id == CampaignParticipant.user_id)
            .where(CampaignParticipant.campaign_id == campaign_id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "creator_id": user.twitter_handle,
                "user_id": participant.user_id,
                "status": participant.status,
                "has_followed": participant.has_followed,
                "has_replied": participant.has_replied,
                "has_retweeted": participant.has_retweeted,
                "has_quoted": participant.has_quoted,
                "chain": participant.chain,
                "stellar_wallet": participant.stellar_wallet,
                "solana_wallet": participant.solana_wallet,
            }
            for participant, user in rows
        ]

    async def get_campaign_participant_by_creator(
        self, campaign_id: int, creator_id: str
    ) -> Optional[dict]:
        """Look up a participant by twitter_handle."""
        stmt = (
            select(CampaignParticipant, User)
            .join(User, User.id == CampaignParticipant.user_id)
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                User.twitter_handle == creator_id,
            )
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if not row:
            return None
        participant, user = row
        return {
            "creator_id": user.twitter_handle,
            "user_id": participant.user_id,
            "status": participant.status,
            "has_followed": participant.has_followed,
            "has_replied": participant.has_replied,
            "has_retweeted": participant.has_retweeted,
            "has_quoted": participant.has_quoted,
            "chain": participant.chain,
            "stellar_wallet": participant.stellar_wallet,
            "solana_wallet": participant.solana_wallet,
        }

    # ------------------------------------------------------------------
    # PaymentIntent CRUD — anti-replay + durable log
    # ------------------------------------------------------------------

    async def get_payment_intent(self, intent_id: str) -> Optional[PaymentIntent]:
        stmt = select(PaymentIntent).where(PaymentIntent.intent_id == intent_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_payment_intent_by_creator(
        self, campaign_id: int, creator_id: str
    ) -> Optional[PaymentIntent]:
        stmt = select(PaymentIntent).where(
            PaymentIntent.campaign_id == campaign_id,
            PaymentIntent.creator_id == creator_id,
            PaymentIntent.status.in_(["submitted", "confirmed"]),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_payment_intent(
        self,
        intent_id: str,
        campaign_id: int,
        creator_id: str,
        amount_usdc: float,
    ) -> PaymentIntent:
        intent = PaymentIntent(
            intent_id=intent_id,
            campaign_id=campaign_id,
            creator_id=creator_id,
            amount_usdc=amount_usdc,
            status="pending",
        )
        self.session.add(intent)
        await self.session.flush()
        await self.session.commit()
        return intent

    async def update_payment_intent(
        self,
        intent_id:   str,
        status:      str,
        tx_hash:     Optional[str] = None,
        receipt_pqc: Optional[str] = None,
    ) -> None:
        stmt = select(PaymentIntent).where(PaymentIntent.intent_id == intent_id)
        result = await self.session.execute(stmt)
        intent = result.scalars().first()
        if not intent:
            return
        intent.status = status
        if tx_hash:
            intent.arc_tx_hash = tx_hash
        if receipt_pqc:
            intent.receipt_pqc = receipt_pqc
        if status in ("submitted", "confirmed"):
            intent.executed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.commit()

    async def list_payment_intents_by_campaign(
        self, campaign_id: int
    ) -> list[PaymentIntent]:
        stmt = select(PaymentIntent).where(PaymentIntent.campaign_id == campaign_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_stale_pending_intents(self) -> list[PaymentIntent]:
        """Retorna intents presos em 'pending' (criados mas nunca enviados para a chain)."""
        stmt = select(PaymentIntent).where(PaymentIntent.status == "pending")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # CctpTransfer CRUD — recovery pós-crash de burn->attest->receive multi-chain
    # ------------------------------------------------------------------

    async def get_cctp_transfer(self, intent_id: str) -> Optional[CctpTransfer]:
        stmt = select(CctpTransfer).where(CctpTransfer.intent_id == intent_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_cctp_transfer(
        self,
        intent_id: str,
        direction: str,
        source_domain: int,
        dest_domain: int,
        counterparty: str,
        amount_usdc: float,
        campaign_id: Optional[int] = None,
    ) -> CctpTransfer:
        transfer = CctpTransfer(
            intent_id=intent_id,
            campaign_id=campaign_id,
            direction=direction,
            source_domain=source_domain,
            dest_domain=dest_domain,
            counterparty=counterparty,
            amount_usdc=amount_usdc,
            status="pending",
        )
        self.session.add(transfer)
        await self.session.flush()
        await self.session.commit()
        return transfer

    async def update_cctp_transfer(
        self,
        intent_id: str,
        status: str,
        source_tx_hash: Optional[str] = None,
        message_hash: Optional[str] = None,
        dest_tx_hash: Optional[str] = None,
        receipt_pqc: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        stmt = select(CctpTransfer).where(CctpTransfer.intent_id == intent_id)
        result = await self.session.execute(stmt)
        transfer = result.scalars().first()
        if not transfer:
            return
        transfer.status = status
        if source_tx_hash:
            transfer.source_tx_hash = source_tx_hash
        if message_hash:
            transfer.message_hash = message_hash
        if dest_tx_hash:
            transfer.dest_tx_hash = dest_tx_hash
        if receipt_pqc:
            transfer.receipt_pqc = receipt_pqc
        if error_message:
            transfer.error_message = error_message
        if status in ("received", "failed"):
            transfer.executed_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def list_stale_pending_cctp_transfers(self) -> list[CctpTransfer]:
        """Espelha list_stale_pending_intents — recovery pós-restart de transfers presos
        antes do burn ter sido confirmado (status='pending')."""
        stmt = select(CctpTransfer).where(CctpTransfer.status == "pending")
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # SettledPayment — feed de tração persistido (sobrevive a restart)
    # ------------------------------------------------------------------

    async def get_settled_payment(self, intent_id: str) -> Optional[SettledPayment]:
        stmt = select(SettledPayment).where(SettledPayment.intent_id == intent_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_settled_payment(
        self,
        intent_id:      str,
        creator_handle: str,
        amount_usdc:    float,
        tx:             str,
        latency_ms:     float,
        ts:             Optional[str] = None,
    ) -> bool:
        """Persiste um pagamento liquidado. Retorna False se intent_id já existe (idempotente)."""
        if await self.get_settled_payment(intent_id):
            return False

        settled_at = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
        payment = SettledPayment(
            intent_id=intent_id,
            creator_handle=creator_handle,
            amount_usdc=amount_usdc,
            tx=tx,
            latency_ms=latency_ms,
            settled_at=settled_at,
        )
        self.session.add(payment)
        try:
            await self.session.flush()
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            return False
        return True

    async def list_settled_payments(self) -> list[SettledPayment]:
        """Todos os pagamentos liquidados em ordem cronológica — usado para hidratar
        o estado in-memory de server/metrics.py no boot do app."""
        stmt = select(SettledPayment).order_by(SettledPayment.settled_at.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
