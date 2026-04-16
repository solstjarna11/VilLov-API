# app/api/auth.py

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from app.config import DEFAULT_SIGNIN_USER_ID
from app.db.database import get_db
from app.schemas.auth import (
    PasskeyAssertionBeginResponse,
    PasskeyAssertionFinishRequest,
    PasskeyBeginRequest,
    PasskeyRegistrationBeginResponse,
    PasskeyRegistrationFinishRequest,
    SessionToken,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/.well-known/apple-app-site-association", include_in_schema=False)
def apple_app_site_association():
    return JSONResponse(
        content={
            "webcredentials": {
                "apps": ["OUR_TEAM_ID.com.our.bundleid"]
            }
        },
        media_type="application/json",
    )

@router.post("/passkey/register/begin")
def passkey_register_begin(
    request: PasskeyBeginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasskeyRegistrationBeginResponse:
    logger.info(
        "auth register begin requested user_handle=%s device_id=%s",
        request.userHandle,
        request.deviceID,
    )
    return AuthService(db).begin_register_passkey(
        user_id=request.userHandle or DEFAULT_SIGNIN_USER_ID,
        device_id=request.deviceID,
    )


@router.post("/passkey/register/finish")
def passkey_register_finish(
    request: PasskeyRegistrationFinishRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SessionToken:
    logger.info(
        "auth register finish requested user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_register_passkey(request)


@router.post("/passkey/login/begin")
def passkey_login_begin(
    request: PasskeyBeginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasskeyAssertionBeginResponse:
    logger.info(
        "auth login begin requested user_handle=%s device_id=%s",
        request.userHandle,
        request.deviceID,
    )
    return AuthService(db).begin_login_passkey(
        user_id=request.userHandle or DEFAULT_SIGNIN_USER_ID,
        device_id=request.deviceID,
    )


@router.post("/passkey/login/finish")
def passkey_login_finish(
    request: PasskeyAssertionFinishRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SessionToken:
    logger.info(
        "auth login finish requested user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_login_passkey(request)


# Optional legacy compatibility
@router.post("/passkey/begin")
def passkey_begin(
    request: PasskeyBeginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PasskeyAssertionBeginResponse:
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
    request: PasskeyAssertionFinishRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SessionToken:
    logger.info(
        "legacy passkey finish requested user_handle=%s credential_id=%s device_id=%s",
        request.userHandle,
        request.credentialID,
        request.deviceID,
    )
    return AuthService(db).finish_login_passkey(request)