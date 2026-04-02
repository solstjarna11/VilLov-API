from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select


from app.config import  TOKEN_TTL_DAYS
from app.db.models import KeyBundle, AuthSession, User, Device

SEEDED_USERS = [
    ("user_alice", "Alice Johnson"),
    ("user_bob", "Bob Smith"),
    ("user_charlie", "Charlie Brown"),
]


def _token_for_user(user_id: str) -> str:
    return f"dev-token-{user_id}"

def _device_id_for_user(user_id: str) -> str:
    return f"device-{user_id}-iphone"

def issue_dev_token(user_id: str) -> tuple[str, datetime]:
    return _token_for_user(user_id), datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS)


def seed_db(db: Session) -> None:

    now =datetime.now(UTC)
    existing_users = {
        user.user_id: user
        for user in db.scalars(select(User)).all()
    }

    for user_id, display_name in SEEDED_USERS:
        user = existing_users.get(user_id)
        if user is None:
            db.add(
                User(
                    user_id=user_id,
                    display_name=display_name,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            user.display_name = display_name
            user.updated_at = now

    db.commit()

    for user_id, _ in SEEDED_USERS:
        device_id = _device_id_for_user(user_id)

        existing_device = db.execute(
            select(Device).where(Device.device_id == device_id)
        ).scalar_one_or_none()

        if existing_device is None:
            db.add(
                Device(
                    device_id=device_id,
                    user_id=user_id,
                    device_name=f"{user_id} iPhone",
                    platform="ios",
                    created_at=now,
                    last_seen_at=now,
                    is_active=True,
                )
            )
        else:
            existing_device.last_seen_at = now
            existing_device.is_active = True

        existing_bundle = db.get(KeyBundle, user_id)
        if existing_bundle is None:
            db.add(
                KeyBundle(
                    user_id=user_id,
                    identity_key=f"stub-identity-key-{user_id}",
                    signed_prekey=f"stub-signed-prekey-{user_id}",
                    signed_prekey_signature=f"stub-signature-{user_id}",
                    one_time_prekey=f"stub-onetime-prekey-{user_id}",
                )
            )

        token = _token_for_user(user_id)
        existing_session = db.execute(
            select(AuthSession).where(AuthSession.access_token == token)
        ).scalar_one_or_none()

        expires_at = now + timedelta(days=TOKEN_TTL_DAYS)

        if existing_session is None:
            db.add(
                AuthSession(
                    user_id=user_id,
                    device_id=device_id,
                    access_token=token,
                    expires_at=expires_at,
                    created_at=now,
                    revoked_at=None,
                )
            )
        else:
            existing_session.user_id = user_id
            existing_session.device_id = device_id
            existing_session.expires_at = expires_at
            existing_session.revoked_at = None
    db.commit()


def issue_dev_token(user_id: str) -> tuple[str, datetime]:
    return _token_for_user(user_id), datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS)
