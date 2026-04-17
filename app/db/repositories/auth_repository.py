# app/db/repositories/auth_repository.py

from sqlalchemy.orm import Session

from app.db.models import AuthSession


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_session_by_access_token(self, access_token: str):
        return (
            self.db.query(AuthSession)
            .filter(AuthSession.access_token == access_token)
            .first()
        )