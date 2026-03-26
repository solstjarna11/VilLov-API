import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.keys import RecipientKeyBundle, UploadKeysRequest
from app.services.key_service import KeyService

router = APIRouter(prefix="/keys", tags=["keys"])
logger = logging.getLogger(__name__)


@router.get("/{user_id}/bundle", response_model=RecipientKeyBundle)
def get_key_bundle(
    user_id: str,
    _current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecipientKeyBundle:
    logger.info("key bundle lookup for user_id=%s", user_id)
    bundle = KeyService(db).get_bundle(user_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key bundle not found")
    return bundle


@router.post("/upload", response_model=RecipientKeyBundle)
def upload_keys(
    request: UploadKeysRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RecipientKeyBundle:
    if request.userID != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot upload keys for another user")
    logger.info("key bundle upload for user_id=%s", request.userID)
    return KeyService(db).upload_keys(request)
