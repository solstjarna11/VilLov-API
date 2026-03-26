from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer


class SendCiphertextRequest(BaseModel):
    recipientUserID: str
    messageID: UUID
    conversationID: UUID
    ciphertext: str
    header: str
    sentAt: datetime


class MessageAckRequest(BaseModel):
    messageID: UUID


class CiphertextEnvelope(BaseModel):
    id: UUID = Field(...)
    senderUserID: str
    recipientUserID: str
    conversationID: UUID
    ciphertext: str
    header: str
    createdAt: datetime

    @field_serializer("createdAt")
    def serialize_created_at(self, value: datetime, _info):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.isoformat().replace("+00:00", "Z")


class SendCiphertextResponse(BaseModel):
    accepted: bool
    envelope: CiphertextEnvelope


class MessageAckResponse(BaseModel):
    acknowledged: bool
    messageID: UUID