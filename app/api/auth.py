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


@router.post("/passkey/begin")
def passkey_begin(_request: PasskeyBeginRequest, db: Annotated[Session, Depends(get_db)]) -> PasskeyBeginResponse:
    logger.info("passkey begin requested")
    return AuthService(db).begin_passkey()


@router.post("/passkey/finish")
def passkey_finish(request: PasskeyFinishRequest, db: Annotated[Session, Depends(get_db)]) -> SessionToken:
    logger.info("passkey finish requested for credential_id=%s", request.credentialID)
    return AuthService(db).finish_passkey(request)
