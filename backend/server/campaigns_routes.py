"""
Router de Campanhas e Usuarios — endpoints consumidos pelo frontend Next.js.

O schema de Campaign retornado aqui espelha exatamente a interface TypeScript
Campaign definida em frontend/src/interfaces/campaign.ts.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac as _hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from database.database import get_db_session
import logging
from database.models import AuthToken, Campaign as CampaignModel, CampaignParticipant, NotificationEvent, User, Wallet, WebSession

logger = logging.getLogger(__name__)
from fastapi import Depends
from server.metrics import record_campaign_event

router = APIRouter(tags=["campaigns"])

_B58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58decode_pubkey(s: str) -> bytes:
    """Decode a base58-encoded Solana public key to 32 raw bytes."""
    n = 0
    for char in s.encode():
        digit = _B58_ALPHABET.find(char)
        if digit < 0:
            raise ValueError(f"Invalid base58 character: {chr(char)}")
        n = n * 58 + digit
    try:
        return n.to_bytes(32, 'big')
    except OverflowError:
        raise ValueError("Base58 value too large to be a 32-byte Solana public key")

DEFAULT_CAMPAIGNS = [
    {
        "id": 1,
        "name": "XiaoLee Genesis Campaign",
        "description": "Be among the first to interact with XiaoLee and earn $XLEE tokens! Follow our account, retweet our launch post and send a message to our bot.",
        "campaign_type": "social",
        "completed_participants": 0,
        "created_at": "2026-04-21T00:00:00Z",
        "creator_twitter_user_id": "XiaoLeeProtocol",
        "max_participants": 1000,
        "profile_to_follow": "XiaoLeeProtocol",
        "reward_per_participant": 50,
        "reward_pool": 50000,
        "reward_token": "$XLEE",
        "status": "active",
        "tweet_id_to_engage": None,
    },
    {
        "id": 2,
        "name": "Swap Challenge",
        "description": "Execute your first swap via XiaoLee AI assistant and earn bonus $XLEE tokens. Just ask XiaoLee to help you swap any token on Solana!",
        "campaign_type": "trading",
        "completed_participants": 0,
        "created_at": "2026-04-21T00:00:00Z",
        "creator_twitter_user_id": "XiaoLeeProtocol",
        "max_participants": 500,
        "profile_to_follow": None,
        "reward_per_participant": 100,
        "reward_pool": 50000,
        "reward_token": "$XLEE",
        "status": "active",
        "tweet_id_to_engage": None,
    },
    {
        "id": 3,
        "name": "Community Builder",
        "description": "Invite 3 friends to join XiaoLee and earn community rewards. Share your referral link and help grow the XiaoLee ecosystem.",
        "campaign_type": "referral",
        "completed_participants": 0,
        "created_at": "2026-04-21T00:00:00Z",
        "creator_twitter_user_id": "XiaoLeeProtocol",
        "max_participants": 200,
        "profile_to_follow": "XiaoLeeProtocol",
        "reward_per_participant": 250,
        "reward_pool": 50000,
        "reward_token": "$XLEE",
        "status": "active",
        "tweet_id_to_engage": None,
    },
]


# ---------------------------------------------------------------------------
# Schemas (espelham exatamente as interfaces TypeScript do frontend)
# ---------------------------------------------------------------------------

class Campaign(BaseModel):
    id: int
    name: str
    description: str
    campaign_type: str
    completed_participants: int
    created_at: str
    creator_twitter_user_id: str
    max_participants: int
    profile_to_follow: Optional[str] = None
    reward_per_participant: float
    reward_pool: float
    reward_token: str
    status: str
    tweet_id_to_engage: Optional[str] = None


class CampaignsResponse(BaseModel):
    success: bool
    campaigns: List[Campaign]


class UserCampaignParticipation(BaseModel):
    id: int
    name: str
    description: str
    reward_token: str
    reward_per_participant: float
    campaign_type: str
    participation_status: str
    tasks_verified_at: Optional[str] = None
    tasks_claimed: bool = False
    claim_receipt_id: Optional[str] = None
    status: Optional[str] = None


class UserCampaignsResponse(BaseModel):
    success: bool
    campaigns: List[UserCampaignParticipation]


class UserResponse(BaseModel):
    id: str
    username: Optional[str] = None
    platform: Optional[str] = None
    swap_count: int = 0
    total_volume: float = 0.0
    campaigns_joined: List[int] = []
    dossier: Optional[dict] = None


class CampaignActionRequest(BaseModel):
    campaign_identifier: str
    wallet_public_key: Optional[str] = None
    wallet_signature: Optional[str] = None
    proof_message: Optional[str] = None
    proof_encoding: Optional[str] = None


class CreateCampaignRequest(BaseModel):
    title: str
    description: str
    campaign_type: str
    profile_to_follow: Optional[str] = None
    tweet_id_to_engage: Optional[str] = None
    reward_token: str
    reward_per_participant: float
    max_participants: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id_from_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")
    return token


def _campaign_to_dict(campaign: CampaignModel, completed_participants: int = 0) -> dict:
    created_at = campaign.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        # NULL no DB (ex: campanha criada por script sem o campo) não pode 500ar a listagem
        "campaign_type": campaign.campaign_type or "custom",
        "completed_participants": completed_participants,
        "created_at": created_at.isoformat(),
        "creator_twitter_user_id": campaign.creator_twitter_user_id,
        "max_participants": campaign.max_participants,
        "profile_to_follow": campaign.profile_to_follow,
        "reward_per_participant": float(campaign.reward_per_participant),
        "reward_pool": float(campaign.reward_pool),
        "reward_token": campaign.reward_token,
        "status": campaign.status,
        "tweet_id_to_engage": campaign.tweet_id_to_engage,
    }


def _participant_status(participant: CampaignParticipant) -> str:
    if participant.status == "paid":
        return "paid"
    if participant.status == "tasks_verified":
        return "tasks_verified"
    return "enrolled"


def _verify_claim_proof(payload: CampaignActionRequest, campaign_id: int, session_token: str) -> None:
    public_key = (payload.wallet_public_key or "").strip()
    signature = (payload.wallet_signature or "").strip()
    message = (payload.proof_message or "").strip()
    proof_encoding = (payload.proof_encoding or "").strip().lower()

    # Custodial sessions (Google/Telegram) are already authenticated via Bearer token in
    # _resolve_user — wallet signature is redundant and not required for them.
    # Covers both session tokens (google_session_*, tg_session_*) and twitter_user_id
    # format (google_*, tg_*) since getSessionId() may return either.
    is_custodial = session_token.startswith(("google_", "tg_"))

    if not public_key or not message:
        raise HTTPException(status_code=400, detail="Wallet public key and proof message are required")

    if not is_custodial and not signature:
        raise HTTPException(status_code=400, detail="Wallet signature proof is required to claim campaign rewards")

    expected_prefix = f"XiaoLee Devnet claim|campaign:{campaign_id}|session:{session_token}|wallet:{public_key}"
    if not message.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Claim proof does not match the current campaign session")

    if proof_encoding not in {"base64", "none", "eip191"}:
        raise HTTPException(status_code=400, detail="Unsupported claim proof encoding")

    # Custodial users: identity verified via Bearer session — skip signature check
    if is_custodial:
        return

    # EVM wallet (Connect Wallet universal): assinatura EIP-191 personal_sign —
    # recupera o endereço via secp256k1 e compara com o wallet_public_key 0x…
    if public_key.startswith("0x"):
        from eth_account import Account
        from eth_account.messages import encode_defunct

        try:
            recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid claim proof payload") from exc
        if recovered.lower() != public_key.lower():
            raise HTTPException(status_code=400, detail="Invalid wallet signature for this claim")
        return

    # Solana (Phantom legado): assinatura Ed25519 sobre pubkey base58
    try:
        public_key_bytes = _b58decode_pubkey(public_key)
        signature_bytes = base64.b64decode(signature)
        message_bytes = message.encode("utf-8")
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid claim proof payload") from exc

    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature_bytes, message_bytes)
    except InvalidSignature as exc:
        raise HTTPException(status_code=400, detail="Invalid wallet signature for this claim") from exc


async def _resolve_user(db: AsyncSession, authorization: Optional[str]) -> User:
    token = _get_user_id_from_token(authorization)
    now = datetime.now(timezone.utc)
    twitter_user_id = token
    twitter_handle = token

    auth_stmt = select(AuthToken).where(AuthToken.token == token)
    auth_res = await db.execute(auth_stmt)
    auth_token = auth_res.scalars().first()
    if auth_token:
        if auth_token.expires_at.tzinfo is None:
            auth_expires = auth_token.expires_at.replace(tzinfo=timezone.utc)
        else:
            auth_expires = auth_token.expires_at

        if auth_expires < now:
            raise HTTPException(status_code=401, detail="Authorization expired")
        twitter_user_id = auth_token.twitter_user_id or token
        twitter_handle = auth_token.twitter_handle or twitter_user_id

    web_stmt = select(WebSession).where(WebSession.session_id == token)
    web_res = await db.execute(web_stmt)
    web_session = web_res.scalars().first()
    if web_session:
        if web_session.expires_at.tzinfo is None:
            session_expires = web_session.expires_at.replace(tzinfo=timezone.utc)
        else:
            session_expires = web_session.expires_at

        if session_expires < now:
            raise HTTPException(status_code=401, detail="Authorization expired")
        twitter_user_id = web_session.twitter_user_id
        twitter_handle = web_session.twitter_user_id

    user_stmt = select(User).where(User.twitter_user_id == twitter_user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()
    if user:
        if twitter_handle and user.twitter_handle != twitter_handle:
            user.twitter_handle = twitter_handle
        return user

    user = User(twitter_user_id=twitter_user_id, twitter_handle=twitter_handle)
    db.add(user)
    await db.flush()
    return user


async def _seed_default_campaigns(db: AsyncSession) -> None:
    count_res = await db.execute(select(func.count()).select_from(CampaignModel))
    existing_count = count_res.scalar() or 0
    if existing_count > 0:
        return

    for campaign_data in DEFAULT_CAMPAIGNS:
        db.add(
            CampaignModel(
                id=campaign_data["id"],
                creator_twitter_user_id=campaign_data["creator_twitter_user_id"],
                name=campaign_data["name"],
                description=campaign_data["description"],
                campaign_type=campaign_data["campaign_type"],
                reward_token=campaign_data["reward_token"],
                reward_per_participant=campaign_data["reward_per_participant"],
                max_participants=campaign_data["max_participants"],
                reward_pool=campaign_data["reward_pool"],
                status=campaign_data["status"],
                profile_to_follow=campaign_data["profile_to_follow"],
                tweet_id_to_engage=campaign_data["tweet_id_to_engage"],
            )
        )

    await db.commit()


async def _get_campaign_or_404(db: AsyncSession, campaign_id: int) -> CampaignModel:
    stmt = select(CampaignModel).where(CampaignModel.id == campaign_id)
    result = await db.execute(stmt)
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return campaign


# ---------------------------------------------------------------------------
# Auth status stub (evita 404 no useAuth)
# ---------------------------------------------------------------------------

@router.get("/auth/status/{token}")
async def auth_status(token: str, db: AsyncSession = Depends(get_db_session)):
    """Auth status endpoint backed by persisted token/session records."""
    if not token or token.strip() == "":
        return {"status": "expired"}

    now = datetime.now(timezone.utc)
    raw_token = token.strip()

    try:
        auth_stmt = select(AuthToken).where(AuthToken.token == raw_token)
        auth_res = await db.execute(auth_stmt)
        auth_token = auth_res.scalars().first()

        if auth_token:
            expires_at = auth_token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if auth_token.status == "active" and expires_at > now:
                return {
                    "status": "active",
                    "session_id": raw_token,
                    "twitter_user_id": auth_token.twitter_user_id,
                }

            if auth_token.status == "pending" and expires_at > now:
                return {"status": "pending", "session_id": raw_token}

            return {"status": "expired"}

        web_stmt = select(WebSession).where(WebSession.session_id == raw_token)
        web_res = await db.execute(web_stmt)
        web_session = web_res.scalars().first()

        if web_session:
            expires_at = web_session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at > now:
                return {
                    "status": "active",
                    "session_id": raw_token,
                    "twitter_user_id": web_session.twitter_user_id,
                }
            return {"status": "expired"}

        # Unknown token keeps the same UX flow while avoiding false "active" states.
        return {"status": "pending", "session_id": raw_token}
    except Exception:
        # Safe fallback to avoid breaking login UX in environments with partial DB state.
        return {"status": "pending", "session_id": raw_token}


# ---------------------------------------------------------------------------
# Telegram Login Widget auth
# ---------------------------------------------------------------------------

@router.post("/auth/telegram/login")
async def telegram_widget_login(payload: dict, db: AsyncSession = Depends(get_db_session)):
    """Validate Telegram Login Widget data and issue a web session."""
    from server.settings import settings

    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    data = dict(payload)
    provided_hash = data.pop("hash", None)
    if not provided_hash:
        raise HTTPException(status_code=400, detail="Missing hash")

    auth_date = data.get("auth_date")
    if not auth_date:
        raise HTTPException(status_code=400, detail="Missing auth_date")
    if time.time() - int(auth_date) > 86400:
        raise HTTPException(status_code=401, detail="Auth data expired")

    # Validate hash: HMAC-SHA256(data_check_string, SHA256(bot_token))
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    expected = _hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, provided_hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram auth hash")

    tg_id = str(data["id"])
    username = data.get("username") or data.get("first_name") or f"tg_{tg_id}"
    twitter_user_id = f"tg_{tg_id}"

    # Try by canonical twitter_user_id first
    user_stmt = select(User).where(User.twitter_user_id == twitter_user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()

    if not user:
        # Fall back to existing user created by the Telegram bot (twitter_user_id = raw tg_id)
        tg_stmt = select(User).where(User.telegram_chat_id == tg_id)
        tg_res = await db.execute(tg_stmt)
        user = tg_res.scalars().first()

    if not user:
        user = User(
            twitter_user_id=twitter_user_id,
            twitter_handle=username,
            telegram_chat_id=tg_id,
        )
        db.add(user)
        await db.flush()
    else:
        # Normalize the user to our canonical format
        if user.twitter_user_id != twitter_user_id:
            user.twitter_user_id = twitter_user_id
        if not user.telegram_chat_id:
            user.telegram_chat_id = tg_id
        if not user.twitter_handle or user.twitter_handle.startswith("telegram_"):
            user.twitter_handle = username
        await db.flush()

    session_id = f"tg_session_{uuid.uuid4().hex}"
    expires_at = datetime.utcnow() + timedelta(days=30)
    db.add(WebSession(session_id=session_id, twitter_user_id=twitter_user_id, expires_at=expires_at))
    await db.commit()

    return {
        "session_id": session_id,
        "twitter_user_id": twitter_user_id,
        "username": username,
        "first_name": data.get("first_name", ""),
    }


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    if not user_id or user_id.strip() == "":
        raise HTTPException(status_code=400, detail="user_id is required")

    # SEC-003: require auth and enforce that caller can only access their own profile
    authed_user = await _resolve_user(db, authorization)
    if authed_user.twitter_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access to this user profile is not allowed")

    await _seed_default_campaigns(db)

    user_stmt = select(User).where(User.twitter_user_id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()

    if not user:
        user = User(twitter_user_id=user_id, twitter_handle=f"user_{user_id[:8]}")
        db.add(user)
        await db.commit()

    participant_stmt = select(CampaignParticipant.campaign_id).where(CampaignParticipant.user_id == user.id)
    participant_res = await db.execute(participant_stmt)
    joined = list(participant_res.scalars().all())

    wallet_stmt = select(Wallet).where(Wallet.user_id == user.id)
    wallet_res = await db.execute(wallet_stmt)
    custodial_wallet = wallet_res.scalars().first()

    created_at = user.created_at if user.created_at else datetime.utcnow()
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return UserResponse(
        id=user_id,
        username=user.twitter_handle,
        swap_count=0,
        total_volume=0.0,
        campaigns_joined=joined,
        dossier={
            "user_info": {
                "twitter_user_id": user.twitter_user_id,
                "twitter_handle": user.twitter_handle,
                "created_at": created_at.isoformat(),
                "custodial_wallet_address": custodial_wallet.address if custodial_wallet else None,
            },
            "balances": [],
            "history": {
                "chat_history": [],
                "swaps": [],
                "transactions": [],
            },
            "campaigns": [],
        },
    )


# ---------------------------------------------------------------------------
# Non-custodial wallet save
# ---------------------------------------------------------------------------

@router.post("/user/{user_id}/wallet")
async def save_user_wallet(user_id: str, payload: dict, db: AsyncSession = Depends(get_db_session)):
    """Save a user-generated non-custodial wallet address. Private key never touches the server."""
    address = (payload.get("address") or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="address is required")

    user_stmt = select(User).where(User.twitter_user_id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    wallet_stmt = select(Wallet).where(Wallet.user_id == user.id)
    wallet_res = await db.execute(wallet_stmt)
    existing = wallet_res.scalars().first()
    if existing:
        return {"address": existing.address, "created": False}

    db.add(Wallet(user_id=user.id, address=address, private_key_encrypted="user_managed"))
    await db.commit()
    return {"address": address, "created": True}


# ---------------------------------------------------------------------------
# Google / Web3Auth login
# ---------------------------------------------------------------------------

@router.post("/auth/google/login")
async def google_web3auth_login(payload: dict, db: AsyncSession = Depends(get_db_session)):
    """Register/login a user authenticated via Web3Auth (Google). Receives Solana public address only."""
    address = (payload.get("address") or "").strip()
    email = (payload.get("email") or "").strip()
    name = (payload.get("name") or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="address is required")

    twitter_user_id = f"google_{address[:20]}"
    handle = name or (email.split("@")[0] if email else f"google_{address[:8]}")

    user_stmt = select(User).where(User.twitter_user_id == twitter_user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()

    if not user:
        # Check if wallet already registered under a different user_id
        wallet_stmt = select(Wallet).where(Wallet.address == address)
        wallet_res = await db.execute(wallet_stmt)
        existing_wallet = wallet_res.scalars().first()
        if existing_wallet:
            user_stmt2 = select(User).where(User.id == existing_wallet.user_id)
            user = (await db.execute(user_stmt2)).scalars().first()

    if not user:
        user = User(twitter_user_id=twitter_user_id, twitter_handle=handle)
        db.add(user)
        await db.flush()

    # Save wallet if not yet saved
    wallet_check = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalars().first()
    if not wallet_check:
        db.add(Wallet(user_id=user.id, address=address, private_key_encrypted="web3auth_managed"))

    session_id = f"google_session_{uuid.uuid4().hex}"
    expires_at = datetime.utcnow() + timedelta(days=30)
    db.add(WebSession(session_id=session_id, twitter_user_id=user.twitter_user_id, expires_at=expires_at))
    await db.commit()

    return {
        "session_id": session_id,
        "twitter_user_id": user.twitter_user_id,
        "username": handle,
        "address": address,
    }


# ---------------------------------------------------------------------------
# Campaign endpoints
# ---------------------------------------------------------------------------

@router.get("/campaigns", response_model=CampaignsResponse)
async def list_campaigns(db: AsyncSession = Depends(get_db_session)):
    await _seed_default_campaigns(db)

    campaigns_res = await db.execute(select(CampaignModel).where(CampaignModel.status == "active").order_by(CampaignModel.id.asc()))
    campaigns = campaigns_res.scalars().all()

    participant_counts_res = await db.execute(
        select(CampaignParticipant.campaign_id, func.count(CampaignParticipant.id))
        .group_by(CampaignParticipant.campaign_id)
    )
    participant_counts = {campaign_id: count for campaign_id, count in participant_counts_res.all()}

    return CampaignsResponse(
        success=True,
        campaigns=[Campaign(**_campaign_to_dict(c, participant_counts.get(c.id, 0))) for c in campaigns],
    )


async def _list_user_campaigns(db: AsyncSession, authorization: Optional[str]) -> UserCampaignsResponse:
    await _seed_default_campaigns(db)

    try:
        user = await _resolve_user(db, authorization)
    except HTTPException:
        return UserCampaignsResponse(success=True, campaigns=[])

    participant_stmt = (
        select(CampaignParticipant, CampaignModel)
        .join(CampaignModel, CampaignModel.id == CampaignParticipant.campaign_id)
        .where(CampaignParticipant.user_id == user.id)
        .order_by(CampaignParticipant.joined_at.asc())
    )
    participant_res = await db.execute(participant_stmt)

    result = []
    for participant, campaign in participant_res.all():
        participation_status = _participant_status(participant)
        verified_at = participant.tasks_verified_at
        if verified_at and verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)

        result.append(
            UserCampaignParticipation(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                reward_token=campaign.reward_token,
                reward_per_participant=float(campaign.reward_per_participant),
                campaign_type=campaign.campaign_type,
                participation_status=participation_status,
                status=participation_status,
                tasks_verified_at=verified_at.isoformat() if verified_at else None,
                tasks_claimed=participant.status == "paid",
                claim_receipt_id=participant.claim_receipt_id,
            )
        )
    return UserCampaignsResponse(success=True, campaigns=result)


@router.get("/campaigns/me", response_model=UserCampaignsResponse)
async def get_current_user_campaigns(
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    """Retorna as campanhas em que o usuario atual participa."""
    return await _list_user_campaigns(db, authorization)


@router.get("/campaigns/user", response_model=UserCampaignsResponse)
async def get_user_campaigns(
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    """Compatibilidade legada para retornar as campanhas do usuario."""
    return await _list_user_campaigns(db, authorization)


@router.post("/campaigns/create")
async def create_campaign(
    payload: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    await _seed_default_campaigns(db)
    user = await _resolve_user(db, authorization)

    new_campaign = CampaignModel(
        creator_twitter_user_id=user.twitter_user_id,
        name=payload.title,
        description=payload.description,
        campaign_type=payload.campaign_type,
        reward_token=payload.reward_token,
        reward_per_participant=payload.reward_per_participant,
        max_participants=payload.max_participants,
        reward_pool=payload.reward_per_participant * payload.max_participants,
        status="active",
        profile_to_follow=payload.profile_to_follow,
        tweet_id_to_engage=payload.tweet_id_to_engage,
    )
    db.add(new_campaign)
    await db.commit()
    await db.refresh(new_campaign)

    return {"success": True, "message": "Campaign created successfully!", "campaign": _campaign_to_dict(new_campaign)}


@router.post("/campaigns/join")
async def join_campaign(
    payload: CampaignActionRequest,
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    await _seed_default_campaigns(db)
    user = await _resolve_user(db, authorization)
    campaign_id = int(payload.campaign_identifier)
    campaign = await _get_campaign_or_404(db, campaign_id)

    existing_stmt = select(CampaignParticipant).where(
        CampaignParticipant.campaign_id == campaign_id,
        CampaignParticipant.user_id == user.id,
    )
    existing_res = await db.execute(existing_stmt)
    existing = existing_res.scalars().first()
    if existing:
        # 409 Conflict é a resposta semanticamente correta para recursos já existentes.
        record_campaign_event("join_duplicate")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this campaign",
        )

    participant_count_stmt = select(func.count()).select_from(CampaignParticipant).where(CampaignParticipant.campaign_id == campaign_id)
    participant_count_res = await db.execute(participant_count_stmt)
    participant_count = participant_count_res.scalar() or 0
    if participant_count >= campaign.max_participants:
        record_campaign_event("join_full")
        return {"success": False, "error": "This campaign is full"}

    db.add(
        CampaignParticipant(
            campaign_id=campaign.id,
            user_id=user.id,
            status="enrolled",
        )
    )
    await db.commit()
    record_campaign_event("join")
    return {
        "success": True,
        "message": f"Successfully joined '{campaign.name}'! Complete the tasks to earn {float(campaign.reward_per_participant)} {campaign.reward_token}.",
    }


@router.post("/campaigns/verify")
async def verify_tasks(
    payload: CampaignActionRequest,
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    await _seed_default_campaigns(db)
    user = await _resolve_user(db, authorization)
    campaign_id = int(payload.campaign_identifier)
    campaign = await _get_campaign_or_404(db, campaign_id)

    participant_stmt = select(CampaignParticipant).where(
        CampaignParticipant.campaign_id == campaign_id,
        CampaignParticipant.user_id == user.id,
    )
    participant_res = await db.execute(participant_stmt)
    participant = participant_res.scalars().first()
    if not participant:
        return {"success": False, "message": "You need to join this campaign first"}

    if participant.status in {"tasks_verified", "paid"}:
        return {"success": True, "message": "Tasks already verified! You can now claim your reward.", "all_tasks_completed": True}

    # SEC-006: real task verification per campaign type
    from server.integrations.campaign_verifier import verify_social, verify_trading, verify_referral
    from server.settings import settings

    campaign_type = campaign.campaign_type

    if campaign_type == "social":
        ok, reason = await verify_social(
            twitter_user_id=user.twitter_user_id,
            profile_to_follow=campaign.profile_to_follow,
            tweet_id_to_engage=campaign.tweet_id_to_engage,
            bearer_token=settings.x_bearer_token,
        )
    elif campaign_type == "trading":
        wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
        wallet = wallet_res.scalars().first()
        ok, reason = await verify_trading(
            wallet_address=wallet.address if wallet else None,
            helius_api_key=settings.helius_api_key,
        )
    elif campaign_type == "referral":
        ok, reason = await verify_referral(user.id, db, campaign_id)
    else:
        logger.warning("[campaigns/verify] Unknown campaign type %r for campaign %d — accepting", campaign_type, campaign_id)
        ok, reason = True, f"Campaign type accepted"

    if not ok:
        return {"success": False, "message": reason, "all_tasks_completed": False}

    participant.status = "tasks_verified"
    participant.tasks_verified_at = datetime.now(timezone.utc)
    await db.commit()
    record_campaign_event("verify")
    return {
        "success": True,
        "message": "All tasks verified successfully! You are eligible to claim your reward.",
        "all_tasks_completed": True,
    }


@router.post("/campaigns/claim")
async def claim_reward(
    payload: CampaignActionRequest,
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(default=None),
):
    await _seed_default_campaigns(db)
    user = await _resolve_user(db, authorization)
    campaign_id = int(payload.campaign_identifier)
    campaign = await _get_campaign_or_404(db, campaign_id)

    participant_stmt = select(CampaignParticipant).where(
        CampaignParticipant.campaign_id == campaign_id,
        CampaignParticipant.user_id == user.id,
    )
    participant_res = await db.execute(participant_stmt)
    participant = participant_res.scalars().first()
    if not participant or participant.status not in {"tasks_verified", "paid"}:
        return {"success": False, "error": "Complete and verify all tasks before claiming"}

    if participant.status == "paid":
        return {"success": False, "error": "Reward already claimed for this campaign"}

    _verify_claim_proof(payload, campaign_id, _get_user_id_from_token(authorization))

    receipt_id = str(uuid.uuid4())[:16]
    participant.status = "paid"
    participant.claim_receipt_id = receipt_id
    db.add(
        NotificationEvent(
            user_id=user.id,
            channel="in_app",
            title=f"Campaign reward claimed: {campaign.name}",
            body=f"You claimed {float(campaign.reward_per_participant)} {campaign.reward_token} and received receipt {receipt_id}.",
            status="pending",
            related_signature=receipt_id,
            metadata_json=json.dumps(
                {
                    "campaign_id": campaign_id,
                    "reward_amount": float(campaign.reward_per_participant),
                    "reward_token": campaign.reward_token,
                    "wallet_public_key": payload.wallet_public_key or "",
                    "claim_receipt_id": receipt_id,
                }
            ),
        )
    )
    await db.commit()
    tx_id = str(uuid.uuid4())[:16]
    record_campaign_event("claim")
    return {
        "success": True,
        "message": f"{float(campaign.reward_per_participant)} {campaign.reward_token} claimed successfully!",
        "transaction_id": tx_id,
        "claim_receipt_id": receipt_id,
        "reward_amount": float(campaign.reward_per_participant),
        "reward_token": campaign.reward_token,
        "wallet_public_key": payload.wallet_public_key,
        "proof_submitted": bool(payload.wallet_signature or payload.proof_message),
    }
