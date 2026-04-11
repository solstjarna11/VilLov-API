import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, AuthenticatedPrincipal
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
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GetOrCreateConversationResponse:
    logger.info(
        "conversation get-or-create current_user_id=%s recipient_user_id=%s",
        principal.user_id,
        request.recipientUserID,
        principal.session_id
    )
    conversation = ConversationService(db).get_or_create(principal.user_id, request.recipientUserID)
    return GetOrCreateConversationResponse(conversationID=conversation.id)

@router.get("")
def list_conversations(
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),):
    conversations = ConversationService(db).list_conversations(principal.user_id)
    return [{
        "conversationID": conversation.id,
        "participantAUserID": conversation.participant_a_user_id,
        "participantBUserID": conversation.participant_b_user_id,
        "createdAt": conversation.created_at,
    }
    for conversation in conversations
    ]
