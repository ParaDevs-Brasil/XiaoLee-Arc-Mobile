from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db_session
from database.models import NotificationEvent, User

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    channel: str
    title: str
    body: str
    status: str
    related_signature: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class AckResponse(BaseModel):
    success: bool
    notification_id: int
    status: str


def _get_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authorization required")

    return token


async def _list_user_notifications(db: AsyncSession, twitter_user_id: str):
    user_stmt = select(User).where(User.twitter_user_id == twitter_user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(NotificationEvent).where(NotificationEvent.user_id == user.id).order_by(NotificationEvent.id.desc())
    result = await db.execute(stmt)
    notifications = []
    for notification in result.scalars().all():
        metadata = {}
        if notification.metadata_json:
            try:
                metadata = json.loads(notification.metadata_json)
            except Exception:
                metadata = {"raw": notification.metadata_json}

        notifications.append(
            NotificationResponse(
                id=notification.id,
                channel=notification.channel,
                title=notification.title,
                body=notification.body,
                status=notification.status,
                related_signature=notification.related_signature,
                metadata=metadata,
            )
        )

    return {"success": True, "notifications": notifications}


@router.get("/me")
async def list_current_notifications(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    twitter_user_id = _get_bearer_token(authorization)
    return await _list_user_notifications(db, twitter_user_id)


@router.get("/{twitter_user_id}")
async def list_notifications(
    twitter_user_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    token = _get_bearer_token(authorization)
    if token != twitter_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await _list_user_notifications(db, twitter_user_id)


@router.post("/{notification_id}/ack", response_model=AckResponse)
async def ack_notification(
    notification_id: int,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    token = _get_bearer_token(authorization)

    stmt = select(NotificationEvent).where(NotificationEvent.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    user_stmt = select(User).where(User.id == notification.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()
    if not user or user.twitter_user_id != token:
        raise HTTPException(status_code=403, detail="Forbidden")

    notification.status = "delivered"
    notification.delivered_at = notification.delivered_at or datetime.now(timezone.utc)
    await db.commit()

    return AckResponse(success=True, notification_id=notification.id, status=notification.status)