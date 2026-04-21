# app/api/keys.py

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import AuthenticatedPrincipal, get_current_user
from app.schemas.keys import (
    OneTimePreKeyCountResponse,
    RecipientKeyBundle,
    UploadKeysRequest,
)
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
        "key bundle lookup success requester=%s target_user_id=%s session_id=%s has_identity_key=%s has_identity_agreement_key=%s has_signed_prekey=%s has_one_time_prekey=%s one_time_prekey_id=%s",
        principal.user_id,
        user_id,
        principal.session_id,
        bool(bundle.identityKey),
        bool(bundle.identityAgreementKey),
        bool(bundle.signedPrekey),
        bool(bundle.oneTimePrekey),
        bundle.oneTimePrekeyId,
    )
    return bundle


@router.post("/upload", response_model=RecipientKeyBundle)
def upload_keys(
    request: UploadKeysRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipientKeyBundle:
    if request.userID != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload keys for another user",
        )
    logger.info(
        "key bundle upload user_id=%s session_id=%s has_identity_key=%s has_identity_agreement_key=%s has_signed_prekey=%s one_time_prekeys_count=%s has_legacy_one_time_prekey=%s",
        principal.user_id,
        principal.session_id,
        bool(request.identityKey),
        bool(request.identityAgreementKey),
        bool(request.signedPrekey),
        len(request.oneTimePrekeys),
        bool(request.oneTimePrekey),
    )

    bundle = KeyService(db).upload_keys(principal.user_id, request)

    logger.info(
        "key bundle upload stored user_id=%s session_id=%s has_identity_key=%s has_identity_agreement_key=%s has_signed_prekey=%s",
        principal.user_id,
        principal.session_id,
        bool(bundle.identityKey),
        bool(bundle.identityAgreementKey),
        bool(bundle.signedPrekey),
    )

    return bundle


@router.get("/me/opk-count", response_model=OneTimePreKeyCountResponse)
def get_my_opk_count(
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OneTimePreKeyCountResponse:
    result = KeyService(db).get_remaining_opk_count(principal.user_id)

    logger.info(
        "opk count requester=%s session_id=%s remaining=%s",
        principal.user_id,
        principal.session_id,
        result.remaining,
    )

    return result