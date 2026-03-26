from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import DEFAULT_SIGNIN_USER_ID, TOKEN_TTL_DAYS
from app.db.models import KeyBundle, TokenMapping, User

SEEDED_USERS = [
    ("user_alice", "Alice Johnson"),
    ("user_bob", "Bob Smith"),
    ("user_charlie", "Charlie Nguyen"),
]


def _token_for_user(user_id: str) -> str:
    return f"dev-token-{user_id}"


def seed_db(db: Session) -> None:
    for user_id, display_name in SEEDED_USERS:
        if db.get(User, user_id) is None:
            db.add(User(user_id=user_id, display_name=display_name))

    db.commit()

    for user_id, _ in SEEDED_USERS:
        if db.get(KeyBundle, user_id) is None:
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
        if db.get(TokenMapping, token) is None:
            db.add(
                TokenMapping(
                    access_token=token,
                    user_id=user_id,
                    expires_at=datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS),
                )
            )

    db.commit()


def issue_dev_token(user_id: str) -> tuple[str, datetime]:
    return _token_for_user(user_id), datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS)
