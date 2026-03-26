from sqlalchemy.orm import Session

from app.config import DEFAULT_CHALLENGE, DEFAULT_SIGNIN_USER_ID, DEV_RP_ID
from app.db.repositories.user_repository import UserRepository
from app.db.seed import issue_dev_token
from app.schemas.auth import (
    PasskeyBeginResponse,
    PasskeyFinishRequest,
    SessionToken,
)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.user_repo = UserRepository(db)

    def begin_passkey(self) -> PasskeyBeginResponse:
        return PasskeyBeginResponse(
            challenge=DEFAULT_CHALLENGE,
            relyingPartyID=DEV_RP_ID,
            userID=DEFAULT_SIGNIN_USER_ID,
        )

    def finish_passkey(self, _request: PasskeyFinishRequest) -> SessionToken:
        user_id = _request.userHandle or DEFAULT_SIGNIN_USER_ID
        if self.user_repo.get_user(user_id) is None:
            user_id = DEFAULT_SIGNIN_USER_ID
        access_token, expires_at = issue_dev_token(user_id)
        self.user_repo.create_or_update_token(access_token=access_token, user_id=user_id, expires_at=expires_at)
        return SessionToken(accessToken=access_token, expiresAt=expires_at)
