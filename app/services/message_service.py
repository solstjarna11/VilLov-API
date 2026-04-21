# app/services/message_service.py

import logging

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.db.models import MessageEnvelope
from app.db.repositories.message_repository import MessageRepository
from app.schemas.messages import (
    CiphertextEnvelope,
    MessageAckRequest,
    MessageAckResponse,
    SendCiphertextRequest,
    SendCiphertextResponse,
)
from app.utils.logging_helper import summarize_ciphertext

logger = logging.getLogger(__name__)


class MessageService:
    def __init__(self, db: Session) -> None:
        self.repo = MessageRepository(db)

    def send(self, sender_user_id: str, request: SendCiphertextRequest) -> SendCiphertextResponse:
        cipher_summary = summarize_ciphertext(request.ciphertext)
        logger.info(
            "message service store sender=%s recipient=%s conversation_id=%s message_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
            sender_user_id,
            request.recipientUserID,
            request.conversationID,
            request.messageID,
            cipher_summary["type"],
            cipher_summary["length"],
            cipher_summary["preview"],
        )

        sent_at = request.sentAt
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        else:
            sent_at = sent_at.astimezone(timezone.utc)

        expires_at = request.expiresAt
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = expires_at.astimezone(timezone.utc)

            now = datetime.now(timezone.utc)

            if expires_at <= sent_at:
                raise ValueError("expires_at_must_be_after_sent_at")

            if expires_at <= now:
                raise ValueError("message_already_expired")
            max_expiry = sent_at + timedelta(days=30)
            if expires_at > max_expiry:
                raise ValueError("expires_at_too_far_in_future")

        envelope = MessageEnvelope(
            id=str(request.messageID),
            sender_user_id=sender_user_id,
            recipient_user_id=request.recipientUserID,
            conversation_id=str(request.conversationID),
            ciphertext=request.ciphertext,
            header=request.header,
            created_at=sent_at,
            acknowledged=False,
            expiry_at=expires_at,
        )

        created = self.repo.create(envelope)

        stored_summary = summarize_ciphertext(created.ciphertext)
        logger.info(
            "message service stored sender=%s recipient=%s conversation_id=%s message_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s acknowledged=%s",
            created.sender_user_id,
            created.recipient_user_id,
            created.conversation_id,
            created.id,
            stored_summary["type"],
            stored_summary["length"],
            stored_summary["preview"],
            created.acknowledged,
        )

        return SendCiphertextResponse(accepted=True, envelope=self._to_schema(created))

    def inbox(self, recipient_user_id: str) -> list[CiphertextEnvelope]:
        envelopes = self.repo.inbox_for_user(recipient_user_id)

        logger.info(
            "message service inbox recipient=%s count=%s",
            recipient_user_id,
            len(envelopes),
        )

        return [self._to_schema(item) for item in envelopes]

    def acknowledge(self, recipient_user_id: str, request: MessageAckRequest) -> MessageAckResponse:
        logger.info(
            "message service acknowledge recipient=%s message_id=%s",
            recipient_user_id,
            request.messageID,
        )

        envelope = self.repo.get(str(request.messageID))
        if envelope is None:
            logger.warning(
                "message service acknowledge missing recipient=%s message_id=%s",
                recipient_user_id,
                request.messageID,
            )
            raise ValueError("message_not_found")

        if envelope.recipient_user_id != recipient_user_id:
            logger.warning(
                "message service acknowledge forbidden recipient=%s actual_recipient=%s message_id=%s",
                recipient_user_id,
                envelope.recipient_user_id,
                request.messageID,
            )
            raise PermissionError("not_recipient")

        self.repo.acknowledge(str(request.messageID))

        logger.info(
            "message service acknowledged recipient=%s message_id=%s",
            recipient_user_id,
            request.messageID,
        )

        return MessageAckResponse(acknowledged=True, messageID=request.messageID)

    @staticmethod
    def _to_schema(envelope: MessageEnvelope) -> CiphertextEnvelope:
        created_at = envelope.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        expiry_at=envelope.expiry_at
        if expiry_at is not None:
            if expiry_at.tzinfo is None:
                expiry_at=expiry_at.replace(tzinfo=timezone.utc)
            else:
                expiry_at=expiry_at.astimezone(timezone.utc)

        return CiphertextEnvelope(
            id=envelope.id,
            senderUserID=envelope.sender_user_id,
            recipientUserID=envelope.recipient_user_id,
            conversationID=envelope.conversation_id,
            ciphertext=envelope.ciphertext,
            header=envelope.header,
            createdAt=created_at,
            expiresAt=expiry_at,
        )