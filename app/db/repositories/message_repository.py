# app/db/repositories/message_repository.py

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.db.models import MessageEnvelope
from app.utils.logging_helper import summarize_ciphertext

# logger = logging.getLogger(__name__)


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, envelope: MessageEnvelope) -> MessageEnvelope:
        cipher_summary = summarize_ciphertext(envelope.ciphertext)
        # logger.info(
        #     "message repository insert conversation_id=%s sender=%s recipient=%s message_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
        #     envelope.conversation_id,
        #     envelope.sender_user_id,
        #     envelope.recipient_user_id,
        #     envelope.id,
        #     cipher_summary["type"],
        #     cipher_summary["length"],
        #     cipher_summary["preview"],
        # )

        self.db.add(envelope)
        self.db.commit()
        self.db.refresh(envelope)

        stored_summary = summarize_ciphertext(envelope.ciphertext)
        # logger.info(
        #     "message repository inserted conversation_id=%s sender=%s recipient=%s message_id=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s acknowledged=%s",
        #     envelope.conversation_id,
        #     envelope.sender_user_id,
        #     envelope.recipient_user_id,
        #     envelope.id,
        #     stored_summary["type"],
        #     stored_summary["length"],
        #     stored_summary["preview"],
        #     envelope.acknowledged,
        # )

        return envelope

    def inbox_for_user(self, recipient_user_id: str) -> list[MessageEnvelope]:
        # logger.info(
        #     "message repository inbox query recipient=%s",
        #     recipient_user_id,
        # )

        now = datetime.now(UTC)

        stmt = (
            select(MessageEnvelope)
            .where(
                MessageEnvelope.recipient_user_id == recipient_user_id,
                MessageEnvelope.acknowledged.is_(False),
                or_(
                    MessageEnvelope.expiry_at.is_(None),
                    MessageEnvelope.expiry_at > now,
                ),
            )
            .order_by(MessageEnvelope.created_at.asc())
        )
        rows = list(self.db.scalars(stmt).all())

        # logger.info(
        #     "message repository inbox result recipient=%s count=%s",
        #     recipient_user_id,
        #     len(rows),
        # )

        for row in rows:
            cipher_summary = summarize_ciphertext(row.ciphertext)
            # logger.info(
            #     "message repository inbox item recipient=%s message_id=%s conversation_id=%s sender=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
            #     recipient_user_id,
            #     row.id,
            #     row.conversation_id,
            #     row.sender_user_id,
            #     cipher_summary["type"],
            #     cipher_summary["length"],
            #     cipher_summary["preview"],
            # )

        return rows

    def get(self, message_id: str) -> MessageEnvelope | None:
        envelope = self.db.get(MessageEnvelope, message_id)

        if envelope is None:
            # logger.info("message repository get message_id=%s found=%s", message_id, False)
            return None

        cipher_summary = summarize_ciphertext(envelope.ciphertext)
        # logger.info(
        #     "message repository get message_id=%s found=%s ciphertext_type=%s ciphertext_len=%s ciphertext_preview=%s",
        #     message_id,
        #     True,
        #     cipher_summary["type"],
        #     cipher_summary["length"],
        #     cipher_summary["preview"],
        # )

        return envelope

    def acknowledge_for_recipient(self, message_id: str, recipient_user_id: str) -> bool:
        # logger.info(
        #     "message repository acknowledge attempt message_id=%s recipient=%s",
        #     message_id,
        #     recipient_user_id,
        # )

        stmt = (
            update(MessageEnvelope)
            .where(
                MessageEnvelope.id == message_id,
                MessageEnvelope.recipient_user_id == recipient_user_id,
                MessageEnvelope.acknowledged.is_(False),
            )
            .values(acknowledged=True)
        )

        result = self.db.execute(stmt)
        self.db.commit()

        updated = result.rowcount > 0

        # logger.info(
        #     "message repository acknowledge result message_id=%s recipient=%s updated=%s",
        #     message_id,
        #     recipient_user_id,
        #     updated,
        # )

        return updated

    def delete_for_sender_if_undelivered(self, message_id: str, sender_user_id: str) -> bool:
        # logger.info(
        #     "message repository delete attempt message_id=%s sender=%s",
        #     message_id,
        #     sender_user_id,
        # )

        stmt = (
            delete(MessageEnvelope)
            .where(
                MessageEnvelope.id == message_id,
                MessageEnvelope.sender_user_id == sender_user_id,
                MessageEnvelope.acknowledged.is_(False),
            )
        )

        result = self.db.execute(stmt)
        self.db.commit()

        deleted = result.rowcount > 0

        # logger.info(
        #     "message repository delete result message_id=%s sender=%s deleted=%s",
        #     message_id,
        #     sender_user_id,
        #     deleted,
        # )

        return deleted