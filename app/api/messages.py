import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user_id
from app.schemas.messages import (
    CiphertextEnvelope,
    MessageAckRequest,
    MessageAckResponse,
    SendCiphertextRequest,
    SendCiphertextResponse,
)
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])
logger = logging.getLogger(__name__)


@router.post("/send", response_model=SendCiphertextResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    request: SendCiphertextRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SendCiphertextResponse:
    logger.info(
        "message send sender=%s recipient=%s message_id=%s",
        current_user_id,
        request.recipientUserID,
        request.messageID,
    )
    return MessageService(db).send(current_user_id, request)


@router.get("/inbox", response_model=list[CiphertextEnvelope])
def get_inbox(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CiphertextEnvelope]:
    logger.info("inbox fetch for recipient=%s", current_user_id)
    return MessageService(db).inbox(current_user_id)


@router.post("/ack", response_model=MessageAckResponse)
def acknowledge_message(
    request: MessageAckRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MessageAckResponse:
    logger.info("message ack recipient=%s message_id=%s", current_user_id, request.messageID)
    service = MessageService(db)
    try:
        return service.acknowledge(current_user_id, request)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot acknowledge this message")
