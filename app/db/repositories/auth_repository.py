# app/db/repositories/auth_repository.py

import hashlib
import hmac

from sqlalchemy.orm import Session

from app.config import SESSION_TOKEN_HASH_SECRET
from app.db.models import AuthSession


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_session_by_access_token(self, access_token: str):
        access_token_hash = self._hash_session_token(access_token)

        return (
            self.db.query(AuthSession)
            .filter(AuthSession.access_token == access_token_hash)
            .first()
        )

    @staticmethod
    def _hash_session_token(raw_token: str) -> str:
        return hmac.new(
            SESSION_TOKEN_HASH_SECRET.encode("utf-8"),
            raw_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()