from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.user_repository import UserRepository
from app.db.models import Conversation


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.repo = ConversationRepository(db)
        self.user_repo = UserRepository(db)

    def get_or_create(self, current_user_id: str, recipient_user_id: str) -> Conversation:
        if recipient_user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create a conversation with yourself",
            )

        if self.user_repo.get_user(recipient_user_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient user not found",
            )

        conversation = self.repo.get_by_participants(current_user_id, recipient_user_id)
        if conversation is not None:
            return conversation
        return self.repo.create(current_user_id, recipient_user_id)
    
    def list_conversations(self, current_user_id: str):
        return self.repo.list_for_user(current_user_id)
