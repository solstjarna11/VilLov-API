import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from dataclasses import dataclass

from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.auth_repository import AuthRepository


bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

@dataclass
class AuthenticatedPrincipal:
    user_id: str
    device_id: str | None
    session_id: int



def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials

    session = AuthRepository(db).get_session_by_access_token(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    if session.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked",
        )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    return AuthenticatedPrincipal(
        user_id=session.user.user_id,
        device_id=session.device.device_id if session.device else None,
        session_id=session.id,
    )   


def get_current_user_id(
     principal: AuthenticatedPrincipal = Depends(get_current_user),   
) -> str:
    
    return principal.user_id
