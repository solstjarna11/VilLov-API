from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, field_serializer


class GetOrCreateConversationRequest(BaseModel):
    recipientUserID: str


class GetOrCreateConversationResponse(BaseModel):
    conversationID: UUID


class ConversationListItem(BaseModel):
    conversationID: UUID
    participantAUserID: str
    participantBUserID: str
    createdAt: datetime

    @field_serializer("createdAt")
    def serialize_created_at(self, value: datetime, _info):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.isoformat().replace("+00:00", "Z")