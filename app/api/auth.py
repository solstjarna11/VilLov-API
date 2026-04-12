import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import DEFAULT_SIGNIN_USER_ID
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
def passkey_register_begin(
    request: PasskeyBeginRequest,
    db: Session = Depends(get_db),
) -> PasskeyBeginResponse:
    logger.info(
        "auth register begin requested user_handle=%s device_id=%s",
        request.userHandle,
        request.deviceID,
    )
    return AuthService(db).begin_register_passkey(
        user_id=request.userHandle or DEFAULT_SIGNIN_USER_ID,
        device_id=request.deviceID,
    )


@router.post("/passkey/register/finish", response_model=SessionToken)
def passkey_register_finish(
    request: PasskeyFinishRequest,
    db: Session = Depends(get_db),
) -> SessionToken:
    logger.info(
        "auth register finish requested user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_register_passkey(request)


@router.post("/passkey/login/begin", response_model=PasskeyBeginResponse)
def passkey_login_begin(
    request: PasskeyBeginRequest,
    db: Session = Depends(get_db),
) -> PasskeyBeginResponse:
    logger.info(
        "auth login begin requested user_handle=%s device_id=%s",
        request.userHandle,
        request.deviceID,
    )
    return AuthService(db).begin_login_passkey(
        user_id=request.userHandle or DEFAULT_SIGNIN_USER_ID,
        device_id=request.deviceID,
    )


@router.post("/passkey/login/finish", response_model=SessionToken)
def passkey_login_finish(
    request: PasskeyFinishRequest,
    db: Session = Depends(get_db),
) -> SessionToken:
    logger.info(
        "auth login finish requested user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_login_passkey(request)


@router.post("/passkey/begin", response_model=PasskeyBeginResponse)
def passkey_begin(
    request: PasskeyBeginRequest,
    db: Session = Depends(get_db),
) -> PasskeyBeginResponse:
    logger.info(
        "legacy passkey begin requested user_handle=%s device_id=%s",
        request.userHandle,
        request.deviceID,
    )
    return AuthService(db).begin_login_passkey(
    user_id=request.userHandle or DEFAULT_SIGNIN_USER_ID,
    device_id=request.deviceID,
)


@router.post("/passkey/finish")
def passkey_finish(
    request: PasskeyFinishRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SessionToken:
    logger.info(
        "legacy passkey finish requested for user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_passkey(request)