from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, or_
from app.db.models import Conversation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Conversation


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def canonicalize(user_a: str, user_b: str) -> tuple[str, str]:
        return tuple(sorted((user_a, user_b)))

    def get_by_participants(self, user_a: str, user_b: str) -> Conversation | None:
        participant_a, participant_b = self.canonicalize(user_a, user_b)
        stmt = select(Conversation).where(
            Conversation.participant_a_user_id == participant_a,
            Conversation.participant_b_user_id == participant_b,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, user_a: str, user_b: str) -> Conversation:
        participant_a, participant_b = self.canonicalize(user_a, user_b)
        conversation = Conversation(
            id=str(uuid4()),
            participant_a_user_id=participant_a,
            participant_b_user_id=participant_b,
            created_at=datetime.now(UTC),
        )
        self.db.add(conversation)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_participants(participant_a, participant_b)
            if existing is None:
                raise
            return existing
        self.db.refresh(conversation)
        return conversation
    
    def list_for_user(self, user_id: str) -> list[Conversation]:
        stmt = (select(Conversation).where(or_(Conversation.participant_a_user_id == user_id,
                                               Conversation.participant_b_user_id == user_id,)).order_by(Conversation.created_at.desc()))
        return list(self.db.scalars(stmt).all())
