import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.conversations import (
    GetOrCreateConversationRequest,
    GetOrCreateConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


@router.post("/get-or-create", response_model=GetOrCreateConversationResponse)
def get_or_create_conversation(
    request: GetOrCreateConversationRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> GetOrCreateConversationResponse:
    logger.info(
        "conversation get-or-create current_user_id=%s recipient_user_id=%s",
        current_user_id,
        request.recipientUserID,
    )
    conversation = ConversationService(db).get_or_create(current_user_id, request.recipientUserID)
    return GetOrCreateConversationResponse(conversationID=conversation.id)
