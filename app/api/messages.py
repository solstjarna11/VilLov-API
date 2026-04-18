# app/api/messages.py

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user, AuthenticatedPrincipal
from app.schemas.messages import (
    CiphertextEnvelope,
    MessageAckRequest,
    MessageAckResponse,
    SendCiphertextRequest,
    SendCiphertextResponse,
)
from app.services.message_service import MessageService
from app.utils.logging_helper import summarize_ciphertext

router = APIRouter(prefix="/messages", tags=["messages"])
logger = logging.getLogger(__name__)


@router.post("/send", response_model=SendCiphertextResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    request: SendCiphertextRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendCiphertextResponse:
    cipher_summary = summarize_ciphertext(request.ciphertext)

    logger.info(
        "message send ingress sender=%s recipient=%s conversation_id=%s message_id=%s session_id=%s ciphertext_present=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s base64_like=%s request_fields=%s",
        principal.user_id,
        request.recipientUserID,
        request.conversationID,
        request.messageID,
        principal.session_id,
        cipher_summary["present"],
        cipher_summary["type"],
        cipher_summary["length"],
        cipher_summary["preview"],
        cipher_summary["base64_like"],
        sorted(request.model_dump().keys()),
    )

    service = MessageService(db)
    response = service.send(principal.user_id, request)

    stored_cipher_summary = summarize_ciphertext(response.envelope.ciphertext)
    logger.info(
        "message send accepted sender=%s recipient=%s conversation_id=%s message_id=%s session_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
        principal.user_id,
        request.recipientUserID,
        request.conversationID,
        request.messageID,
        principal.session_id,
        stored_cipher_summary["type"],
        stored_cipher_summary["length"],
        stored_cipher_summary["preview"],
    )

    return response


@router.get("/inbox", response_model=list[CiphertextEnvelope])
def get_inbox(
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CiphertextEnvelope]:
    logger.info(
        "inbox fetch recipient=%s session_id=%s",
        principal.user_id,
        principal.session_id,
    )

    messages = MessageService(db).inbox(principal.user_id)

    for msg in messages:
        cipher_summary = summarize_ciphertext(msg.ciphertext)
        logger.info(
            "inbox item recipient=%s message_id=%s sender=%s conversation_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
            principal.user_id,
            msg.id,
            msg.senderUserID,
            msg.conversationID,
            cipher_summary["type"],
            cipher_summary["length"],
            cipher_summary["preview"],
        )

    return messages


@router.post("/ack", response_model=MessageAckResponse)
def acknowledge_message(
    request: MessageAckRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageAckResponse:
    logger.info(
        "message ack recipient=%s message_id=%s session_id=%s",
        principal.user_id,
        request.messageID,
        principal.session_id,
    )
    service = MessageService(db)
    try:
        return service.acknowledge(principal.user_id, request)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot acknowledge this message")