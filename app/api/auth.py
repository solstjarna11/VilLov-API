import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import (
    PasskeyBeginRequest,
    PasskeyBeginResponse,
    PasskeyFinishRequest,
    SessionToken,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/passkey/register/begin", response_model=PasskeyBeginResponse)
def passkey_register_begin(db: Session=Depends(get_db)) -> PasskeyBeginResponse:
    logger.info("passkey begin requested")
    return AuthService(db).begin_register_passkey()

@router.post("/passkey/register/finish", response_model=SessionToken)
def passkey_register_finish(
    request: PasskeyFinishRequest,
    db: Session = Depends(get_db),
) -> SessionToken:
    return AuthService(db).finish_register_passkey(request)

@router.post("/passkey/login/begin", response_model=PasskeyBeginResponse)
def passkey_login_begin(db: Session = Depends(get_db)) -> PasskeyBeginResponse:
    return AuthService(db).begin_login_passkey()

@router.post("/passkey/login/finish", response_model=SessionToken)
def passkey_login_finish(
    request: PasskeyFinishRequest,
    db: Session = Depends(get_db),
) -> SessionToken:
    return AuthService(db).finish_login_passkey(request)


@router.post("/passkey/begin", response_model=PasskeyBeginResponse)
def passkey_begin(db: Session = Depends(get_db)) -> PasskeyBeginResponse:
    logger.info("passkey begin requested")
    return AuthService(db).begin_passkey()

@router.post("/passkey/finish")
def passkey_finish(request: PasskeyFinishRequest, db: Annotated[Session, Depends(get_db)]) -> SessionToken:
    logger.info("passkey finish requested for credential_id=%s", request.credentialID)
    return AuthService(db).finish_passkey(request)
