import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
import importlib

app_module = importlib.import_module("server.app")
from database.database import get_db_session
from database.models import NotificationEvent, User


client = TestClient(app_module.app)


@pytest.mark.asyncio
async def test_list_notifications_returns_user_notifications(db_session):
    user = User(twitter_handle="@alice", twitter_user_id="alice-1", telegram_chat_id="2002")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    older = NotificationEvent(
        user_id=user.id,
        channel="in_app",
        title="Primeira",
        body="Primeira notificacao",
        status="pending",
        related_signature="sig-1",
        metadata_json='{"kind":"first"}',
    )
    newer = NotificationEvent(
        user_id=user.id,
        channel="telegram",
        title="Segunda",
        body="Segunda notificacao",
        status="delivered",
        related_signature="sig-2",
        metadata_json="not-json",
    )
    db_session.add(older)
    db_session.add(newer)
    await db_session.commit()

    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    try:
        me_response = client.get("/v1/notifications/me", headers={"Authorization": "Bearer alice-1"})
        assert me_response.status_code == 200
        assert me_response.json()["success"] is True

        response = client.get("/v1/notifications/alice-1", headers={"Authorization": "Bearer alice-1"})
        assert response.status_code == 200

        payload = response.json()
        assert payload["success"] is True
        assert len(payload["notifications"]) == 2

        # Endpoint orders by id desc, so latest event appears first.
        first_item = payload["notifications"][0]
        second_item = payload["notifications"][1]
        assert first_item["related_signature"] == "sig-2"
        assert first_item["metadata"] == {"raw": "not-json"}
        assert second_item["related_signature"] == "sig-1"
        assert second_item["metadata"] == {"kind": "first"}
    finally:
        app_module.app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_notifications_returns_404_for_unknown_user(db_session):
    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = client.get("/v1/notifications/unknown-user", headers={"Authorization": "Bearer unknown-user"})
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"
    finally:
        app_module.app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_notifications_rejects_cross_user_access(db_session):
    user = User(twitter_handle="@alice", twitter_user_id="alice-1", telegram_chat_id="2002")
    db_session.add(user)
    await db_session.commit()

    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = client.get("/v1/notifications/alice-1", headers={"Authorization": "Bearer bob-1"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"
    finally:
        app_module.app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_notification_ack_updates_status(db_session):
    user = User(twitter_handle="@bob", twitter_user_id="bob-1", telegram_chat_id="1001")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    notification = NotificationEvent(
        user_id=user.id,
        channel="in_app",
        title="Swap confirmado",
        body="Seu swap foi concluido.",
        status="pending",
        related_signature="sig-ack",
    )
    db_session.add(notification)
    await db_session.commit()
    await db_session.refresh(notification)

    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = client.post(
            f"/v1/notifications/{notification.id}/ack",
            headers={"Authorization": "Bearer bob-1"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        updated = (await db_session.execute(select(NotificationEvent).where(NotificationEvent.id == notification.id))).scalar_one()
        assert updated.status == "delivered"
        assert updated.delivered_at is not None
    finally:
        app_module.app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_notification_ack_rejects_wrong_user(db_session):
    user = User(twitter_handle="@bob", twitter_user_id="bob-1", telegram_chat_id="1001")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    notification = NotificationEvent(
        user_id=user.id,
        channel="in_app",
        title="Swap confirmado",
        body="Seu swap foi concluido.",
        status="pending",
        related_signature="sig-ack",
    )
    db_session.add(notification)
    await db_session.commit()

    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = client.post(
            f"/v1/notifications/{notification.id}/ack",
            headers={"Authorization": "Bearer alice-1"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"
    finally:
        app_module.app.dependency_overrides.pop(get_db_session, None)