from uuid import UUID

from pydantic import BaseModel


class GetOrCreateConversationRequest(BaseModel):
    recipientUserID: str


class GetOrCreateConversationResponse(BaseModel):
    conversationID: UUID
