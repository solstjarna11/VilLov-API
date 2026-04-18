# app/db/repositories/message_repository.py

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MessageEnvelope


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, envelope: MessageEnvelope) -> MessageEnvelope:
        self.db.add(envelope)
        self.db.commit()
        self.db.refresh(envelope)
        return envelope

    def inbox_for_user(self, recipient_user_id: str) -> list[MessageEnvelope]:
        stmt = (
            select(MessageEnvelope)
            .where(
                MessageEnvelope.recipient_user_id == recipient_user_id,
                MessageEnvelope.acknowledged.is_(False),
            )
            .order_by(MessageEnvelope.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get(self, message_id: str) -> MessageEnvelope | None:
        return self.db.get(MessageEnvelope, message_id)

    def acknowledge(self, message_id: str) -> None:
        envelope = self.db.get(MessageEnvelope, message_id)
        if envelope is None:
            return
        envelope.acknowledged = True
        self.db.commit()
