from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TokenMapping, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def create_or_update_token(self, access_token: str, user_id: str, expires_at: datetime) -> TokenMapping:
        token = self.db.get(TokenMapping, access_token)
        if token is None:
            token = TokenMapping(access_token=access_token, user_id=user_id, expires_at=expires_at)
            self.db.add(token)
        else:
            token.user_id = user_id
            token.expires_at = expires_at
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_user_id_by_token(self, access_token: str) -> str | None:
        stmt = select(TokenMapping.user_id).where(TokenMapping.access_token == access_token)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.user_id)).all())
