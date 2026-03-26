from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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


class SendCiphertextResponse(BaseModel):
    accepted: bool
    envelope: CiphertextEnvelope


class MessageAckResponse(BaseModel):
    acknowledged: bool
    messageID: UUID
