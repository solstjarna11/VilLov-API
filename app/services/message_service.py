from sqlalchemy.orm import Session
from datetime import timezone

from app.db.models import MessageEnvelope
from app.db.repositories.message_repository import MessageRepository
from app.schemas.messages import (
    CiphertextEnvelope,
    MessageAckRequest,
    MessageAckResponse,
    SendCiphertextRequest,
    SendCiphertextResponse,
)


class MessageService:
    def __init__(self, db: Session) -> None:
        self.repo = MessageRepository(db)

    def send(self, sender_user_id: str, request: SendCiphertextRequest) -> SendCiphertextResponse:
        envelope = MessageEnvelope(
            id=str(request.messageID),
            sender_user_id=sender_user_id,
            recipient_user_id=request.recipientUserID,
            conversation_id=str(request.conversationID),
            ciphertext=request.ciphertext,
            header=request.header,
            created_at=request.sentAt,
            acknowledged=False,
        )
        created = self.repo.create(envelope)
        return SendCiphertextResponse(accepted=True, envelope=self._to_schema(created))

    def inbox(self, recipient_user_id: str) -> list[CiphertextEnvelope]:
        envelopes = self.repo.inbox_for_user(recipient_user_id)
        return [self._to_schema(item) for item in envelopes]

    def acknowledge(self, recipient_user_id: str, request: MessageAckRequest) -> MessageAckResponse:
        envelope = self.repo.get(str(request.messageID))
        if envelope is None:
            raise ValueError("message_not_found")
        if envelope.recipient_user_id != recipient_user_id:
            raise PermissionError("not_recipient")
        self.repo.acknowledge(str(request.messageID))
        return MessageAckResponse(acknowledged=True, messageID=request.messageID)

    from datetime import timezone

    @staticmethod
    def _to_schema(envelope: MessageEnvelope) -> CiphertextEnvelope:
        created_at = envelope.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        return CiphertextEnvelope(
            id=envelope.id,
            senderUserID=envelope.sender_user_id,
            recipientUserID=envelope.recipient_user_id,
            conversationID=envelope.conversation_id,
            ciphertext=envelope.ciphertext,
            header=envelope.header,
            createdAt=created_at,
        )
