# app/api/keys.py

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, AuthenticatedPrincipal
from app.schemas.keys import RecipientKeyBundle, UploadKeysRequest
from app.services.key_service import KeyService

router = APIRouter(prefix="/keys", tags=["keys"])
logger = logging.getLogger(__name__)


@router.get("/{user_id}/bundle", response_model=RecipientKeyBundle)
def get_key_bundle(
    user_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipientKeyBundle:
    logger.info(
        "key bundle lookup requester=%s target_user_id=%s session_id=%s",
        principal.user_id,
        user_id,
        principal.session_id,
    )
    bundle = KeyService(db).get_bundle(user_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key bundle not found")

    logger.info(
        "key bundle lookup success requester=%s target_user_id=%s session_id=%s has_identity_key=%s has_signed_prekey=%s one_time_prekeys_count=%s",
        principal.user_id,
        user_id,
        principal.session_id,
        bool(getattr(bundle, "identityKey", None)),
        bool(getattr(bundle, "signedPrekey", None)),
        len(getattr(bundle, "oneTimePrekey", []) or []),
    )
    return bundle


@router.post("/upload", response_model=RecipientKeyBundle)
def upload_keys(
    request: UploadKeysRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipientKeyBundle:
    if request.userID != principal.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot upload keys for another user")

    logger.info(
        "key bundle upload user_id=%s session_id=%s has_identity_key=%s has_signed_prekey=%s one_time_prekeys_count=%s",
        request.userID,
        principal.session_id,
        bool(getattr(request, "identityKey", None)),
        bool(getattr(request, "signedPrekey", None)),
        len(getattr(request, "oneTimePrekey", []) or []),
    )

    bundle = KeyService(db).upload_keys(request)

    logger.info(
        "key bundle upload stored user_id=%s session_id=%s has_identity_key=%s has_signed_prekey=%s one_time_prekeys_count=%s",
        request.userID,
        principal.session_id,
        bool(getattr(bundle, "identityKey", None)),
        bool(getattr(bundle, "signedPrekey", None)),
        len(getattr(bundle, "oneTimePrekey", []) or []),
    )

    return bundle